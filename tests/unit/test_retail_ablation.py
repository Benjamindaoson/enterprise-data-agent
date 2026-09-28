from __future__ import annotations

from eiw.retail.ablation import RetailHarnessAblationRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.runtime import RetailBARuntime


def test_retail_harness_ablation_reports_same_operator_comparison() -> None:
    result = RetailHarnessAblationRunner(
        RetailBARuntime(RetailDataEngine.demo())
    ).run()

    assert result["suite"] == "RetailHarnessAblation-v1"
    assert result["cases"] == 10
    assert 0.0 <= result["intrinsic_rank_driver_recall_at_k"] <= 1.0
    assert 0.0 <= result["query_aware_driver_recall_at_k"] <= 1.0
    assert result["parallel_execution"]["sequential_mean_ms"] >= 0.0
    assert result["parallel_execution"]["parallel_mean_ms"] >= 0.0
