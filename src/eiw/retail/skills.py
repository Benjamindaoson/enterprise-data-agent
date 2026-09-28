"""Typed specialist analytical agents for the retail BA Agent."""

from __future__ import annotations

from eiw.retail.data import RetailDataEngine
from eiw.retail.models import WorkstreamName, WorkstreamResult
from eiw.retail.specialist_policy import (
    SPECIALIST_SKILLS,
    SpecialistDecision,
    SpecialistPolicy,
    deterministic_specialist_decision,
)


class RetailAnalyticalWorkers:
    """Specialist agents that plan within bounded analytical skill allowlists.

    The default policy executes the full verified deterministic skill set.
    When a model policy is configured, each specialist independently chooses
    its skill subset; execution still happens through deterministic data
    operators rather than arbitrary model-generated SQL.
    """

    def __init__(
        self,
        data: RetailDataEngine,
        *,
        policy: SpecialistPolicy | None = None,
    ) -> None:
        self.data = data
        self.policy = policy

    def _decision(
        self,
        workstream: WorkstreamName,
        question: str,
    ) -> tuple[SpecialistDecision, str]:
        if self.policy is not None:
            try:
                decision = self.policy.decide(
                    workstream=workstream,
                    question=question,
                    allowed_skills=SPECIALIST_SKILLS[workstream],
                )
                allowed = set(SPECIALIST_SKILLS[workstream])
                filtered: list[str] = []
                for skill in decision.skills:
                    if skill in allowed and skill not in filtered:
                        filtered.append(skill)
                if not filtered:
                    filtered = list(SPECIALIST_SKILLS[workstream])
                return (
                    decision.model_copy(update={"skills": filtered}),
                    "model",
                )
            except Exception:
                fallback = deterministic_specialist_decision(workstream)
                return (
                    fallback.model_copy(
                        update={
                            "rationale": (
                                "Specialist model unavailable; deterministic "
                                "verified skill set used."
                            )
                        }
                    ),
                    "deterministic-fallback",
                )
        return deterministic_specialist_decision(workstream), "deterministic"

    @staticmethod
    def _metadata(
        decision: SpecialistDecision,
        source: str,
    ) -> dict[str, object]:
        return {
            "policy_source": source,
            "selected_skills": list(decision.skills),
            "rationale": decision.rationale,
        }

    def run(
        self,
        name: WorkstreamName,
        current: list[int],
        previous: list[int],
        *,
        question: str = "",
    ) -> WorkstreamResult:
        handlers = {
            WorkstreamName.OVERVIEW: self.overview,
            WorkstreamName.STORE: self.store,
            WorkstreamName.PRODUCT: self.product,
            WorkstreamName.PROMOTION: self.promotion,
            WorkstreamName.CUSTOMER: self.customer,
        }
        return handlers[name](current, previous, question=question)

    def overview(
        self,
        current: list[int],
        previous: list[int],
        *,
        question: str = "",
    ) -> WorkstreamResult:
        decision, source = self._decision(WorkstreamName.OVERVIEW, question)
        metrics = (
            self.data.overview(current, previous)
            if "kpi_overview" in decision.skills
            else {}
        )
        sales_change = float(metrics.get("sales_change_pct") or 0.0)
        direction = "down" if sales_change < 0 else "up"
        summary = (
            f"Sales are {direction} {abs(sales_change):.1f}% versus the "
            "comparison period."
            if metrics
            else "Overview specialist selected no executable KPI skill."
        )
        return WorkstreamResult(
            name=WorkstreamName.OVERVIEW,
            summary=summary,
            metrics=metrics,
            metadata=self._metadata(decision, source),
        )

    def store(
        self,
        current: list[int],
        previous: list[int],
        *,
        question: str = "",
    ) -> WorkstreamResult:
        decision, source = self._decision(WorkstreamName.STORE, question)
        rows = (
            self.data.contribution("store", current, previous, limit=12)
            if "store_contribution" in decision.skills
            else []
        )
        anomalies = (
            self.data.store_anomalies(current, limit=8)
            if "store_anomaly" in decision.skills
            else []
        )
        cross_scan = (
            self.data.cross_dimension_scan(current, previous, limit=20)
            if "store_commodity_scan" in decision.skills
            else []
        )
        worst = next(
            (row for row in rows if float(row["delta"]) < 0),
            rows[0] if rows else None,
        )
        summary = (
            f"Store {worst['segment']} is the largest listed negative contributor."
            if worst
            else "No store contribution was selected or available."
        )
        return WorkstreamResult(
            name=WorkstreamName.STORE,
            summary=summary,
            rows=rows,
            artifacts=[
                {"type": "store_anomalies", "rows": anomalies},
                {"type": "store_commodity_scan", "rows": cross_scan},
            ],
            metadata=self._metadata(decision, source),
        )

    def product(
        self,
        current: list[int],
        previous: list[int],
        *,
        question: str = "",
    ) -> WorkstreamResult:
        decision, source = self._decision(WorkstreamName.PRODUCT, question)
        rows = (
            self.data.contribution("commodity", current, previous, limit=12)
            if "commodity_contribution" in decision.skills
            else []
        )
        price_volume = (
            self.data.price_volume_decomposition(current, previous, limit=12)
            if "price_volume" in decision.skills
            else []
        )
        worst = next(
            (row for row in rows if float(row["delta"]) < 0),
            rows[0] if rows else None,
        )
        summary = (
            f"{worst['segment']} is the largest listed commodity driver."
            if worst
            else "No product contribution was selected or available."
        )
        return WorkstreamResult(
            name=WorkstreamName.PRODUCT,
            summary=summary,
            rows=rows,
            artifacts=[
                {"type": "price_volume_decomposition", "rows": price_volume}
            ],
            metadata=self._metadata(decision, source),
        )

    def promotion(
        self,
        current: list[int],
        previous: list[int],
        *,
        question: str = "",
    ) -> WorkstreamResult:
        decision, source = self._decision(WorkstreamName.PROMOTION, question)
        rows = (
            self.data.promotion_performance(current, limit=12)
            if "merchandising" in decision.skills
            else []
        )
        summary = (
            f"{rows[0]['display_location']} has the highest observed sales "
            "among display states."
            if rows
            else "No promotion or merchandising observation was selected or available."
        )
        return WorkstreamResult(
            name=WorkstreamName.PROMOTION,
            summary=summary,
            rows=rows,
            metadata=self._metadata(decision, source),
        )

    def customer(
        self,
        current: list[int],
        previous: list[int],
        *,
        question: str = "",
    ) -> WorkstreamResult:
        decision, source = self._decision(WorkstreamName.CUSTOMER, question)
        customers = (
            self.data.customer_segments(current, limit=10)
            if "customer_segments" in decision.skills
            else []
        )
        pairs = (
            self.data.basket_affinity(current, limit=10)
            if "basket_affinity" in decision.skills
            else []
        )
        income = (
            self.data.demographic_contribution(
                "income",
                current,
                previous,
                limit=10,
            )
            if "income_segments" in decision.skills
            else []
        )
        household_comp = (
            self.data.demographic_contribution(
                "household_comp",
                current,
                previous,
                limit=10,
            )
            if "household_composition" in decision.skills
            else []
        )
        coupon_funnel = (
            self.data.coupon_funnel(limit=10)
            if "coupon_funnel" in decision.skills
            else []
        )

        summary = (
            f"Top customer generated {float(customers[0]['sales']):.1f} sales "
            "in the analysis window."
            if customers
            else "No customer concentration result was selected or available."
        )
        if income:
            biggest = income[0]
            summary += (
                f" Income segment {biggest['segment']} has the largest observed "
                f"period sales movement ({float(biggest['delta']):+,.1f})."
            )
        return WorkstreamResult(
            name=WorkstreamName.CUSTOMER,
            summary=summary,
            rows=customers,
            artifacts=[
                {"type": "basket_affinity", "rows": pairs},
                {"type": "demographic_income", "rows": income},
                {"type": "demographic_household_comp", "rows": household_comp},
                {
                    "type": "coupon_funnel",
                    "rows": coupon_funnel,
                    "note": (
                        "Observed campaign targeting/redemption; "
                        "not incremental causal lift."
                    ),
                },
            ],
            metadata=self._metadata(decision, source),
        )
