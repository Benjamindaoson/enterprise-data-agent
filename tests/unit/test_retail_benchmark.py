from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.runtime import RetailBARuntime


def test_retail_analyst_benchmark_is_reproducible() -> None:
    result = RetailBenchmarkRunner(RetailBARuntime(RetailDataEngine.demo())).run()

    assert result["suite"] == "RetailAnalystBench-v1"
    assert result["cases"] == 10
    assert result["gold_method"] == "independent_readonly_sql"
    assert 0 <= result["driver_recall_at_k"] <= 1
    assert 0 <= result["semantic_coverage"] <= 1
    assert result["numeric_accuracy"] == 1.0
    assert result["mean_time_to_first_insight_ms"] >= 0
    assert result["report_completeness"] == 1.0
    assert result["action_coverage"] == 1.0


def test_rolling_retail_benchmark_spans_historical_windows() -> None:
    runner = RetailBenchmarkRunner(RetailBARuntime(RetailDataEngine.demo()))
    cases = runner.build_rolling_cases()

    assert len(cases) == 30
    assert len({case.current_weeks for case in cases}) == 5

    # Full 30-case execution is a real-data workflow gate. Unit CI executes
    # one six-case historical window to keep feedback latency bounded.
    result = runner.run(cases[:6])
    assert result["suite"] == "RetailAnalystBench-Rolling-v1"
    assert result["windows"] == 1
    assert result["cases"] == 6
    assert result["numeric_accuracy"] == 1.0
    assert 0 <= result["driver_recall_at_k"] <= 1
