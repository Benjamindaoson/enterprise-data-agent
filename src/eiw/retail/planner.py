"""Deterministic first-pass investigation planner.

The planner deliberately exposes business workstreams rather than chain-of-thought.
Model-driven planning can be layered on later without changing worker contracts.
"""

from __future__ import annotations

from eiw.retail.models import RetailAnalysisRequest, WorkstreamName


class InvestigationPlanner:
    def plan(self, request: RetailAnalysisRequest) -> list[WorkstreamName]:
        question = request.question.lower()
        selected: list[WorkstreamName] = [WorkstreamName.OVERVIEW]

        if any(token in question for token in ("store", "门店", "region", "区域", "sales", "销售", "performance", "经营")):
            selected.append(WorkstreamName.STORE)
        if any(token in question for token in ("product", "sku", "category", "品类", "商品", "sales", "销售", "performance", "经营")):
            selected.append(WorkstreamName.PRODUCT)
        if any(token in question for token in ("promotion", "promo", "display", "mailer", "促销", "陈列", "经营", "why", "为什么")):
            selected.append(WorkstreamName.PROMOTION)
        if any(token in question for token in ("customer", "basket", "household", "客户", "顾客", "购物篮", "经营")):
            selected.append(WorkstreamName.CUSTOMER)

        if len(selected) == 1:
            selected.extend(
                [
                    WorkstreamName.STORE,
                    WorkstreamName.PRODUCT,
                    WorkstreamName.PROMOTION,
                    WorkstreamName.CUSTOMER,
                ]
            )

        deduped: list[WorkstreamName] = []
        for item in selected:
            if item not in deduped:
                deduped.append(item)
        return deduped[: request.max_workstreams]
