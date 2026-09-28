"""Business investigation planning and replanning.

The planner exposes only business workstream decisions. It does not expose or
persist private model reasoning.
"""

from __future__ import annotations

from eiw.retail.models import RetailAnalysisRequest, WorkstreamName, WorkstreamResult


class InvestigationPlanner:
    def initial_plan(self, request: RetailAnalysisRequest) -> list[WorkstreamName]:
        question = request.question.lower()
        selected = [WorkstreamName.OVERVIEW]

        if any(token in question for token in ("store", "门店", "region", "区域", "sales", "销售", "performance", "经营", "why", "为什么")):
            selected.append(WorkstreamName.STORE)
        if any(token in question for token in ("product", "sku", "category", "品类", "商品", "sales", "销售", "performance", "经营", "why", "为什么")):
            selected.append(WorkstreamName.PRODUCT)
        if any(token in question for token in ("promotion", "promo", "display", "mailer", "促销", "陈列")):
            selected.append(WorkstreamName.PROMOTION)
        if any(
            token in question
            for token in (
                "customer",
                "basket",
                "household",
                "income",
                "age",
                "campaign",
                "coupon",
                "客户",
                "顾客",
                "购物篮",
                "收入",
                "年龄",
                "活动",
                "优惠券",
            )
        ):
            selected.append(WorkstreamName.CUSTOMER)

        if len(selected) == 1:
            selected.extend([WorkstreamName.STORE, WorkstreamName.PRODUCT])

        return self._dedupe(selected)[: request.max_workstreams]

    def replan(
        self,
        request: RetailAnalysisRequest,
        completed: list[WorkstreamResult],
    ) -> list[WorkstreamName]:
        completed_names = {item.name for item in completed}
        question = request.question.lower()
        next_steps: list[WorkstreamName] = []

        overview = next((item for item in completed if item.name == WorkstreamName.OVERVIEW), None)
        sales_change = float(overview.metrics.get("sales_change_pct") or 0.0) if overview else 0.0
        diagnostic_question = any(token in question for token in ("why", "为什么", "原因", "经营", "performance", "sales", "销售"))

        if WorkstreamName.PROMOTION not in completed_names and (
            sales_change < -1.0
            or diagnostic_question
            or any(token in question for token in ("promotion", "promo", "display", "促销", "陈列"))
        ):
            next_steps.append(WorkstreamName.PROMOTION)

        if WorkstreamName.CUSTOMER not in completed_names and (
            diagnostic_question
            or any(
                token in question
                for token in (
                    "customer",
                    "basket",
                    "household",
                    "income",
                    "campaign",
                    "coupon",
                    "客户",
                    "顾客",
                    "购物篮",
                    "收入",
                    "活动",
                    "优惠券",
                )
            )
        ):
            next_steps.append(WorkstreamName.CUSTOMER)

        remaining = max(0, request.max_workstreams - len(completed_names))
        return self._dedupe(next_steps)[:remaining]

    def plan(self, request: RetailAnalysisRequest) -> list[WorkstreamName]:
        """Compatibility alias for callers that only need a one-shot plan."""
        return self.initial_plan(request)

    @staticmethod
    def _dedupe(items: list[WorkstreamName]) -> list[WorkstreamName]:
        deduped: list[WorkstreamName] = []
        for item in items:
            if item not in deduped:
                deduped.append(item)
        return deduped
