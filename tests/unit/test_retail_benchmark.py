from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.runtime import RetailBARuntime


def test_retail_analyst_benchmark_is_reproducible() -> None:
    result = RetailBenchmarkRunner(RetailBARuntime(RetailDataEngine.demo())).run()

    assert result["suite"] == "RetailAnalystBench-smoke-v1"
    assert result["cases"] == 2
    assert 0 <= result["driver_recall_at_k"] <= 1
    assert result["report_completeness"] == 1.0
    assert result["action_coverage"] == 1.0
