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
