from eiw.retail.data import RetailDataEngine
from eiw.retail.models import RetailAnalysisRequest, WorkstreamName
from eiw.retail.runtime import RetailBARuntime


def test_retail_runtime_runs_end_to_end() -> None:
    runtime = RetailBARuntime(RetailDataEngine.demo())
    response = runtime.analyze(
        RetailAnalysisRequest(
            question="Why did recent sales decline? Analyze stores, products, promotions and what to do next."
        )
    )

    assert response.status == "COMPLETED"
    assert response.kpis["sales_change_pct"] < 0
    assert {item.name for item in response.workstreams} >= {
        WorkstreamName.OVERVIEW,
        WorkstreamName.STORE,
        WorkstreamName.PRODUCT,
        WorkstreamName.PROMOTION,
    }
    assert response.insights
    assert response.charts
    assert response.report.actions
    assert response.events[-1].event_type == "analysis_completed"
    assert response.timings_ms["total"] >= 0


def test_merchandising_language_does_not_overclaim_causality() -> None:
    runtime = RetailBARuntime(RetailDataEngine.demo())
    response = runtime.analyze(
        RetailAnalysisRequest(question="Analyze promotion and display performance.")
    )

    merchandising = [item for item in response.insights if item.kind == "merchandising"]
    assert merchandising
    text = " ".join(
        f"{item.finding} {item.business_impact} {item.recommended_action}"
        for item in merchandising
    ).lower()
    assert "association" in text
    assert "matched" in text


def test_runtime_replans_after_initial_diagnostic_wave() -> None:
    runtime = RetailBARuntime(RetailDataEngine.demo())
    response = runtime.analyze(
        RetailAnalysisRequest(question="Why did recent sales decline?")
    )

    event_types = [event.event_type for event in response.events]
    assert "replan_started" in event_types
    assert "replan_ready" in event_types
    assert WorkstreamName.PROMOTION in {item.name for item in response.workstreams}
    assert WorkstreamName.CUSTOMER in {item.name for item in response.workstreams}


def test_insight_selection_preserves_requested_business_dimensions() -> None:
    runtime = RetailBARuntime(RetailDataEngine.demo())
    response = runtime.analyze(
        RetailAnalysisRequest(
            question=(
                "Why did recent sales change by store and category? "
                "Recommend the next action."
            ),
            top_k=3,
        )
    )

    covered = {
        key
        for insight in response.insights
        for key in insight.dimensions
    }
    assert "store" in covered
    assert "commodity" in covered


def test_cross_dimension_discovery_preserves_joint_driver() -> None:
    runtime = RetailBARuntime(RetailDataEngine.demo())
    response = runtime.analyze(
        RetailAnalysisRequest(
            question=(
                "Find the largest recent store and category anomaly and explain "
                "where management should drill down."
            ),
            top_k=3,
        )
    )

    assert any(
        insight.kind == "cross_dimension_driver"
        and "store" in insight.dimensions
        and "commodity" in insight.dimensions
        for insight in response.insights
    )
