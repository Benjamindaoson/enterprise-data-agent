"""Decision-ready business report assembly."""

from __future__ import annotations

from eiw.retail.models import ActionCard, ExecutiveReport, Insight, WorkstreamResult


class RetailReportBuilder:
    def build(
        self,
        *,
        question: str,
        kpis: dict[str, object],
        workstreams: list[WorkstreamResult],
        insights: list[Insight],
    ) -> ExecutiveReport:
        summary = [insight.finding for insight in insights[:4]]
        if not summary:
            summary = ["No material business movement was detected in the selected analysis window."]

        drivers = [
            {
                "title": insight.title,
                "driver": insight.driver,
                "impact": insight.business_impact,
                "score": round(insight.score, 3),
            }
            for insight in insights[:6]
        ]

        opportunities = [
            insight.finding
            for insight in insights
            if insight.kind in {"merchandising", "anomaly"} and insight.score >= 0.35
        ]

        actions: list[ActionCard] = []
        for index, insight in enumerate(insights[:5]):
            target = ", ".join(f"{key}={value}" for key, value in insight.dimensions.items()) or "selected business scope"
            actions.append(
                ActionCard(
                    priority=f"P{min(index, 2)}",
                    action=insight.recommended_action,
                    target=target,
                    rationale=insight.business_impact,
                    monitor_kpi="Sales / units / conversion proxy / availability proxy",
                )
            )

        sections = [
            {"id": "business-performance", "title": "Business Performance", "content": kpis},
            {
                "id": "diagnostics",
                "title": "Store & Product Diagnostics",
                "content": [item.model_dump(mode="json") for item in workstreams if item.name.value in {"store", "product"}],
            },
            {
                "id": "promotion-merchandising",
                "title": "Promotion & Merchandising",
                "content": [item.model_dump(mode="json") for item in workstreams if item.name.value == "promotion"],
            },
            {
                "id": "customer-basket",
                "title": "Customer & Basket",
                "content": [item.model_dump(mode="json") for item in workstreams if item.name.value == "customer"],
            },
        ]

        return ExecutiveReport(
            title="Retail Business Review",
            executive_summary=summary,
            key_drivers=drivers,
            opportunities=opportunities,
            actions=actions,
            monitoring=[
                "Track the highest-impact negative contributors in the next analysis window.",
                "Validate merchandising associations with matched store/product comparisons before rollout.",
                "Re-run the same benchmark after material model, planner, or skill changes.",
            ],
            sections=sections,
        )
