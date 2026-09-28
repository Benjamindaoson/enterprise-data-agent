"""Programmatic insight mining and ranking for retail business analysis."""

from __future__ import annotations

from hashlib import sha1
from math import tanh
from typing import Any

from eiw.retail.models import Insight, WorkstreamName, WorkstreamResult


def _score(*, impact: float, surprise: float, support: float, actionability: float) -> float:
    raw = 0.40 * impact + 0.25 * surprise + 0.20 * support + 0.15 * actionability
    return max(0.0, min(1.0, raw))


def _fingerprint(kind: str, title: str) -> str:
    return sha1(f"{kind}:{title}".encode()).hexdigest()[:12]


class InsightMiner:
    """Extract high-value findings from typed analytical worker results."""

    def mine(self, workstreams: list[WorkstreamResult], *, top_k: int) -> list[Insight]:
        by_name = {item.name: item for item in workstreams}
        candidates: list[Insight] = []

        overview = by_name.get(WorkstreamName.OVERVIEW)
        if overview:
            sales_change = float(overview.metrics.get("sales_change_pct") or 0.0)
            impact = min(1.0, abs(sales_change) / 20.0)
            title = f"Sales changed {sales_change:+.1f}% versus the comparison period"
            candidates.append(
                Insight(
                    insight_id=_fingerprint("performance", title),
                    kind="performance",
                    title=title,
                    finding=overview.summary,
                    driver="Overall business movement",
                    business_impact=f"Period sales moved {sales_change:+.1f}%.",
                    recommended_action="Prioritize the largest negative contributors before applying broad interventions.",
                    score=_score(impact=impact, surprise=impact, support=1.0, actionability=0.8),
                    support=1.0,
                )
            )

        for name, label in (
            (WorkstreamName.STORE, "store"),
            (WorkstreamName.PRODUCT, "commodity"),
        ):
            result = by_name.get(name)
            if not result:
                continue
            negatives = [row for row in result.rows if float(row.get("delta") or 0.0) < 0]
            total_abs = sum(abs(float(row.get("delta") or 0.0)) for row in result.rows) or 1.0
            for row in negatives[:4]:
                delta = float(row["delta"])
                share = abs(delta) / total_abs
                impact = min(1.0, share * 2.0)
                title = f"{label.title()} {row['segment']} is a major negative contributor"
                candidates.append(
                    Insight(
                        insight_id=_fingerprint(f"{label}_driver", title),
                        kind=f"{label}_driver",
                        title=title,
                        finding=f"{row['segment']} contributed {delta:,.1f} of listed sales change.",
                        driver=f"{label.title()} contribution",
                        business_impact=f"{share:.0%} of the absolute listed {label} movement.",
                        recommended_action=f"Drill into {row['segment']} before applying a broad business response.",
                        score=_score(
                            impact=impact,
                            surprise=min(1.0, abs(delta) / 5000.0),
                            support=0.95,
                            actionability=0.90,
                        ),
                        support=0.95,
                        dimensions={label: str(row["segment"])},
                        evidence=[row],
                    )
                )

        store_result = by_name.get(WorkstreamName.STORE)
        if store_result:
            cross_rows: list[dict[str, Any]] = []
            for artifact in store_result.artifacts:
                if artifact.get("type") == "store_commodity_scan":
                    cross_rows = list(artifact.get("rows", []))
                    break
            total_abs_cross = sum(abs(float(row.get("sales_delta") or 0.0)) for row in cross_rows) or 1.0
            for row in cross_rows[:5]:
                delta = float(row.get("sales_delta") or 0.0)
                if delta >= 0:
                    continue
                share = abs(delta) / total_abs_cross
                title = f"Store {row['store_id']} × {row['commodity']} concentrates a high-impact decline"
                candidates.append(
                    Insight(
                        insight_id=_fingerprint("cross_dimension_driver", title),
                        kind="cross_dimension_driver",
                        title=title,
                        finding=(
                            f"The store × commodity slice moved {delta:,.1f} in sales "
                            "versus the comparison window."
                        ),
                        driver="Cross-dimensional store and commodity movement",
                        business_impact=f"{share:.0%} of the absolute scanned store × commodity movement.",
                        recommended_action=(
                            f"Inspect product, promotion and availability proxies for store {row['store_id']} "
                            f"within {row['commodity']} before applying a broad intervention."
                        ),
                        score=_score(
                            impact=min(1.0, share * 3.0),
                            surprise=min(1.0, abs(delta) / 4000.0),
                            support=0.95,
                            actionability=0.95,
                        ),
                        support=0.95,
                        dimensions={
                            "store": str(row["store_id"]),
                            "commodity": str(row["commodity"]),
                        },
                        evidence=[row],
                    )
                )

        product_result = by_name.get(WorkstreamName.PRODUCT)
        if product_result:
            decomposition: list[dict[str, Any]] = []
            for artifact in product_result.artifacts:
                if artifact.get("type") == "price_volume_decomposition":
                    decomposition = list(artifact.get("rows", []))
                    break
            for row in decomposition[:3]:
                delta = float(row.get("sales_delta") or 0.0)
                if abs(delta) < 1e-9:
                    continue
                volume_effect = float(row.get("volume_effect") or 0.0)
                price_effect = float(row.get("price_effect") or 0.0)
                dominant = "volume" if abs(volume_effect) >= abs(price_effect) else "price"
                dominant_value = volume_effect if dominant == "volume" else price_effect
                title = f"{row['commodity']} change is primarily {dominant}-driven"
                candidates.append(
                    Insight(
                        insight_id=_fingerprint("price_volume", title),
                        kind="price_volume",
                        title=title,
                        finding=(
                            f"Sales changed {delta:,.1f}; volume effect is {volume_effect:,.1f} "
                            f"and price effect is {price_effect:,.1f}."
                        ),
                        driver=f"{dominant.title()} effect",
                        business_impact=(
                            f"The dominant {dominant} component contributes {dominant_value:,.1f} "
                            "within the deterministic decomposition."
                        ),
                        recommended_action=(
                            "Prioritize demand/availability diagnostics."
                            if dominant == "volume"
                            else "Review effective price, discount and promotion changes."
                        ),
                        score=_score(
                            impact=min(1.0, abs(delta) / 8000.0),
                            surprise=min(1.0, abs(dominant_value) / 5000.0),
                            support=0.95,
                            actionability=0.85,
                        ),
                        support=0.95,
                        dimensions={"commodity": str(row["commodity"])},
                        evidence=[row],
                    )
                )

        promo = by_name.get(WorkstreamName.PROMOTION)
        if promo and len(promo.rows) >= 2:
            ranked = sorted(promo.rows, key=lambda row: float(row.get("avg_line_sales") or 0.0), reverse=True)
            best, baseline = ranked[0], ranked[-1]
            best_avg = float(best.get("avg_line_sales") or 0.0)
            base_avg = float(baseline.get("avg_line_sales") or 0.0)
            associated = ((best_avg - base_avg) / base_avg * 100.0) if base_avg else 0.0
            title = f"{best['display_location']} is associated with stronger line sales"
            candidates.append(
                Insight(
                    insight_id=_fingerprint("merchandising", title),
                    kind="merchandising",
                    title=title,
                    finding=f"Observed average line sales are {associated:+.1f}% versus {baseline['display_location']}.",
                    driver="Merchandising association",
                    business_impact="The association identifies a candidate merchandising opportunity, not a causal effect.",
                    recommended_action="Run a matched-store/product analysis before scaling the display change.",
                    score=_score(
                        impact=min(1.0, abs(associated) / 50.0),
                        surprise=min(1.0, abs(associated) / 40.0),
                        support=min(1.0, float(best.get("line_items") or 0) / 500.0),
                        actionability=0.80,
                    ),
                    support=min(1.0, float(best.get("line_items") or 0) / 500.0),
                    dimensions={"display": str(best["display_location"])},
                    evidence=[best, baseline],
                )
            )

        customer = by_name.get(WorkstreamName.CUSTOMER)
        if customer:
            income_rows: list[dict[str, Any]] = []
            coupon_rows: list[dict[str, Any]] = []
            for artifact in customer.artifacts:
                if artifact.get("type") == "demographic_income":
                    income_rows = list(artifact.get("rows", []))
                elif artifact.get("type") == "coupon_funnel":
                    coupon_rows = list(artifact.get("rows", []))

            if income_rows:
                row = max(
                    income_rows,
                    key=lambda item: abs(float(item.get("delta") or 0.0)),
                )
                delta = float(row.get("delta") or 0.0)
                share = float(row.get("share_of_absolute_change") or 0.0)
                title = f"Income segment {row['segment']} has the largest customer-mix sales movement"
                candidates.append(
                    Insight(
                        insight_id=_fingerprint("customer_segment_driver", title),
                        kind="customer_segment_driver",
                        title=title,
                        finding=(
                            f"Observed sales for the segment moved {delta:+,.1f} versus "
                            "the comparison window."
                        ),
                        driver="Descriptive customer-segment movement",
                        business_impact=(
                            f"The segment accounts for {share:.0%} of absolute observed "
                            "income-segment sales movement."
                        ),
                        recommended_action=(
                            "Inspect basket composition and store/product mix for this "
                            "segment before designing a targeted intervention."
                        ),
                        score=_score(
                            impact=min(1.0, share * 2.0),
                            surprise=min(1.0, abs(delta) / 5000.0),
                            support=0.85,
                            actionability=0.80,
                        ),
                        support=0.85,
                        dimensions={"income": str(row["segment"])},
                        evidence=[row],
                    )
                )

            if coupon_rows:
                best = max(
                    coupon_rows,
                    key=lambda item: float(item.get("household_redemption_rate") or 0.0),
                )
                rate = float(best.get("household_redemption_rate") or 0.0)
                targeted = int(best.get("targeted_households") or 0)
                title = f"Campaign {best['campaign_id']} has the highest observed household redemption rate"
                candidates.append(
                    Insight(
                        insight_id=_fingerprint("coupon_funnel", title),
                        kind="coupon_funnel",
                        title=title,
                        finding=(
                            f"{rate:.1%} of targeted households have an observed coupon "
                            "redemption in the public campaign records."
                        ),
                        driver="Observed campaign-to-redemption funnel",
                        business_impact=(
                            "This identifies a campaign pattern for follow-up; it does "
                            "not estimate incremental campaign lift."
                        ),
                        recommended_action=(
                            "Compare audience, offer mix and pre-campaign purchase "
                            "behavior before changing campaign allocation."
                        ),
                        score=_score(
                            impact=min(1.0, rate * 4.0),
                            surprise=min(1.0, rate * 5.0),
                            support=min(1.0, targeted / 500.0),
                            actionability=0.75,
                        ),
                        support=min(1.0, targeted / 500.0),
                        dimensions={"campaign": str(best["campaign_id"])},
                        evidence=[best],
                    )
                )

        store = by_name.get(WorkstreamName.STORE)
        if store:
            anomalies: list[dict[str, Any]] = []
            for artifact in store.artifacts:
                if artifact.get("type") == "store_anomalies":
                    anomalies = list(artifact.get("rows", []))
                    break
            for row in anomalies[:2]:
                zscore = float(row.get("zscore") or 0.0)
                if abs(zscore) < 1.5:
                    continue
                title = f"Store {row['store_id']} deviates materially from peer-week sales"
                candidates.append(
                    Insight(
                        insight_id=_fingerprint("anomaly", title),
                        kind="anomaly",
                        title=title,
                        finding=f"Latest store-week sales have a z-score of {zscore:+.2f} against the current peer-week distribution.",
                        driver="Store-level anomaly",
                        business_impact="The deviation warrants targeted diagnostic follow-up.",
                        recommended_action=f"Inspect product and promotion mix for store {row['store_id']}.",
                        score=_score(
                            impact=min(1.0, abs(zscore) / 4.0),
                            surprise=min(1.0, abs(zscore) / 3.0),
                            support=0.75,
                            actionability=0.85,
                        ),
                        support=0.75,
                        dimensions={"store": str(row["store_id"])},
                        evidence=[row],
                    )
                )

        deduped: dict[tuple[str, str], Insight] = {}
        for candidate in candidates:
            key = (candidate.kind, candidate.title)
            previous = deduped.get(key)
            if previous is None or candidate.score > previous.score:
                deduped[key] = candidate

        return sorted(deduped.values(), key=lambda item: item.score, reverse=True)[:top_k]


def bounded_surprise(value: float) -> float:
    """Utility used by future benchmark extensions."""
    return float(tanh(abs(value)))
