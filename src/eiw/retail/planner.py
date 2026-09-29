"""Business investigation planning and replanning.

The planner exposes only public business workstream decisions. It can use an
optional model-driven Supervisor, while deterministic planning remains the
reproducible default and fallback.
"""

from __future__ import annotations

from eiw.retail.models import RetailAnalysisRequest, WorkstreamName, WorkstreamResult
from eiw.retail.supervisor import SupervisorPolicy


class InvestigationPlanner:
    def __init__(self, policy: SupervisorPolicy | None = None) -> None:
        self.policy = policy
        self.last_source = "deterministic"
        self.last_rationale = ""

    def initial_plan(self, request: RetailAnalysisRequest) -> list[WorkstreamName]:
        if self.policy is not None:
            try:
                decision = self.policy.decide(
                    stage="initial",
                    question=self.model_question(request),
                    completed=[],
                    max_workstreams=request.max_workstreams,
                )
                self.last_source = "model"
                self.last_rationale = decision.rationale
                return self._dedupe(
                    [WorkstreamName.OVERVIEW, *decision.workstreams]
                )[: request.max_workstreams]
            except Exception:
                self.last_source = "deterministic-fallback"
                self.last_rationale = (
                    "Model supervisor unavailable; deterministic planner used."
                )

        question = request.question.lower()
        selected = [WorkstreamName.OVERVIEW]

        if any(
            token in question
            for token in (
                "store",
                "门店",
                "region",
                "区域",
                "sales",
                "销售",
                "performance",
                "经营",
                "why",
                "为什么",
            )
        ):
            selected.append(WorkstreamName.STORE)
        if any(
            token in question
            for token in (
                "product",
                "sku",
                "category",
                "品类",
                "商品",
                "sales",
                "销售",
                "performance",
                "经营",
                "why",
                "为什么",
            )
        ):
            selected.append(WorkstreamName.PRODUCT)
        if any(
            token in question
            for token in (
                "promotion",
                "promo",
                "display",
                "mailer",
                "促销",
                "陈列",
            )
        ):
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

        if self.policy is None:
            self.last_source = "deterministic"
            self.last_rationale = ""
        return self._dedupe(selected)[: request.max_workstreams]

    def replan(
        self,
        request: RetailAnalysisRequest,
        completed: list[WorkstreamResult],
    ) -> list[WorkstreamName]:
        completed_names = {item.name for item in completed}
        remaining = max(0, request.max_workstreams - len(completed_names))
        if remaining <= 0:
            return []

        if self.policy is not None:
            try:
                decision = self.policy.decide(
                    stage="replan",
                    question=self.model_question(request),
                    completed=completed,
                    max_workstreams=remaining,
                )
                self.last_source = "model"
                self.last_rationale = decision.rationale
                return self._dedupe(
                    [
                        name
                        for name in decision.workstreams
                        if name not in completed_names
                    ]
                )[:remaining]
            except Exception:
                self.last_source = "deterministic-fallback"
                self.last_rationale = (
                    "Model supervisor unavailable; deterministic replanning used."
                )

        question = request.question.lower()
        next_steps: list[WorkstreamName] = []

        overview = next(
            (
                item
                for item in completed
                if item.name == WorkstreamName.OVERVIEW
            ),
            None,
        )
        sales_change = (
            float(overview.metrics.get("sales_change_pct") or 0.0)
            if overview
            else 0.0
        )
        diagnostic_question = any(
            token in question
            for token in (
                "why",
                "为什么",
                "原因",
                "经营",
                "performance",
                "sales",
                "销售",
            )
        )

        if WorkstreamName.PROMOTION not in completed_names and (
            sales_change < -1.0
            or diagnostic_question
            or any(
                token in question
                for token in (
                    "promotion",
                    "promo",
                    "display",
                    "促销",
                    "陈列",
                )
            )
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

        if self.policy is None:
            self.last_source = "deterministic"
            self.last_rationale = ""
        return self._dedupe(next_steps)[:remaining]

    def plan(self, request: RetailAnalysisRequest) -> list[WorkstreamName]:
        return self.initial_plan(request)

    @staticmethod
    def model_question(request: RetailAnalysisRequest) -> str:
        if not request.memory_context:
            return request.question
        memories = "\n".join(
            f"- {item[:800]}"
            for item in request.memory_context[:6]
            if item.strip()
        )
        if not memories:
            return request.question
        return (
            f"{request.question}\n\n"
            "Relevant prior experience follows. Treat it as non-authoritative "
            "context and verify it against current evidence before using it:\n"
            f"{memories}"
        )

    @staticmethod
    def _dedupe(items: list[WorkstreamName]) -> list[WorkstreamName]:
        deduped: list[WorkstreamName] = []
        for item in items:
            if item not in deduped:
                deduped.append(item)
        return deduped
