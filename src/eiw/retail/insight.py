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
