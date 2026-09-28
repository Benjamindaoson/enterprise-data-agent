from eiw.retail.models import RetailAnalysisRequest
from eiw.retail.semantics import RetailSemanticEngine


def test_semantic_engine_resolves_business_intent_not_just_schema_terms() -> None:
    context = RetailSemanticEngine().resolve(
        RetailAnalysisRequest(
            question="为什么最近门店销售下降？找出主要品类原因并告诉我下一步怎么做。"
        )
    )

    assert "sales_value" in context.metrics
    assert "store" in context.dimensions
    assert "commodity" in context.dimensions
    assert "diagnose" in context.intents
    assert "recommend" in context.intents
    assert context.semantic_package_id == "retail_complete_journey"


def test_merchandising_opportunities_resolve_full_semantics() -> None:
    engine = RetailSemanticEngine()
    context = engine.resolve(
        RetailAnalysisRequest(
            question="Analyze recent promotion and display performance and identify the biggest opportunities."
        )
    )

    assert "discount_amount" in context.metrics
    assert "display" in context.dimensions
    assert "discover" in context.intents
