"""Business semantic resolution for the retail BA Agent."""

from __future__ import annotations

from pathlib import Path

from eiw.retail.models import BusinessQuestionContext, RetailAnalysisRequest
from eiw.semantic.package import SemanticPackage, load_semantic_package

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_PACKAGE = _REPO_ROOT / "semantic_packages/retail_complete_journey/semantic-package.yaml"


class RetailSemanticEngine:
    """Resolve a business question into stable analytical semantics.

    This is deliberately deterministic in the first production slice. A model
    or Wren-backed resolver may replace the parser later while preserving the
    same BusinessQuestionContext contract.
    """

    def __init__(self, package: SemanticPackage | None = None) -> None:
        self.package = package or load_semantic_package(_DEFAULT_PACKAGE)
        self._metric_ids = {metric.id for metric in self.package.metrics}
        self._dimension_ids = {dimension.id for dimension in self.package.dimensions}

    def resolve(self, request: RetailAnalysisRequest) -> BusinessQuestionContext:
        question = request.question.lower()
        metrics: list[str] = []
        dimensions: list[str] = []
        intents: list[str] = []

        self._append_if(metrics, "sales_value", any(t in question for t in ("sales", "revenue", "销售", "营收", "业绩")))
        self._append_if(metrics, "units", any(t in question for t in ("unit", "volume", "销量", "件数")))
        self._append_if(metrics, "baskets", any(t in question for t in ("basket", "transaction", "购物篮", "交易数")))
        self._append_if(metrics, "average_basket_value", any(t in question for t in ("basket value", "客单", "客单价")))
        self._append_if(
            metrics,
            "discount_amount",
            any(t in question for t in ("discount", "coupon", "promotion", "promo", "折扣", "优惠券", "促销")),
        )

        self._append_if(dimensions, "store", any(t in question for t in ("store", "region", "门店", "区域")))
        self._append_if(dimensions, "product", any(t in question for t in ("product", "sku", "商品", "单品")))
        self._append_if(dimensions, "commodity", any(t in question for t in ("category", "commodity", "品类", "类目")))
        self._append_if(dimensions, "household", any(t in question for t in ("customer", "household", "客户", "顾客", "会员")))
        self._append_if(dimensions, "display", any(t in question for t in ("display", "merchandising", "陈列", "货架")))
        self._append_if(dimensions, "week", any(t in question for t in ("week", "周", "最近", "recent")))

        self._append_if(intents, "diagnose", any(t in question for t in ("why", "原因", "为什么", "诊断")))
        self._append_if(intents, "compare", any(t in question for t in ("compare", "versus", "vs", "对比", "比较", "环比", "同比")))
        self._append_if(
            intents,
            "discover",
            any(
                t in question
                for t in (
                    "opportunity",
                    "opportunities",
                    "anomaly",
                    "anomalies",
                    "机会",
                    "异常",
                    "发现",
                )
            ),
        )
        self._append_if(intents, "recommend", any(t in question for t in ("recommend", "action", "怎么办", "建议", "下一步")))
        self._append_if(intents, "report", any(t in question for t in ("report", "summary", "报告", "汇报", "总结")))

        if not intents:
            intents = ["diagnose", "recommend"]
        if not metrics:
            metrics = ["sales_value", "units", "baskets", "average_basket_value"]
        if any(intent in intents for intent in ("diagnose", "discover", "report")):
            for dimension in ("store", "commodity"):
                if dimension not in dimensions:
                    dimensions.append(dimension)
        if not dimensions:
            dimensions = ["store", "commodity", "week"]

        metrics = [metric for metric in metrics if metric in self._metric_ids]
        dimensions = [dimension for dimension in dimensions if dimension in self._dimension_ids]
        return BusinessQuestionContext(
            metrics=metrics,
            dimensions=dimensions,
            time_grain="week",
            entities={},
            constraints={
                "max_workstreams": request.max_workstreams,
                "top_k": request.top_k,
            },
            intents=intents,
            semantic_package_id=self.package.package.id,
            semantic_package_version=self.package.package.version,
            semantic_content_hash=self.package.content_hash,
        )

    @staticmethod
    def _append_if(values: list[str], value: str, condition: bool) -> None:
        if condition and value not in values:
            values.append(value)
