from __future__ import annotations

from collections import Counter

from eiw.retail.adversarial import (
    RetailAdversarialBenchmark,
    all_adversarial_cases,
    build_development_cases,
    load_holdout_cases,
)
from eiw.retail.data import RetailDataEngine
from eiw.retail.runtime import RetailBARuntime


def test_adversarial_suite_has_252_cases_and_balanced_categories() -> None:
    development = build_development_cases()
    holdout = load_holdout_cases()
    cases = all_adversarial_cases()

    assert len(development) == 168
    assert len(holdout) == 84
    assert len(cases) == 252
    counts = Counter(case.category for case in cases)
    assert len(counts) == 14
    assert set(counts.values()) == {18}


def test_frozen_holdout_case_ids_are_unique() -> None:
    cases = load_holdout_cases()
    assert len({case.case_id for case in cases}) == len(cases)


def test_representative_adversarial_cases_fail_closed() -> None:
    runtime = RetailBARuntime(RetailDataEngine.demo())
    runner = RetailAdversarialBenchmark(runtime)
    cases = load_holdout_cases()
    critical = {
        "prompt_injection",
        "adversarial_prompts",
        "missing_data",
        "unsupported_causality",
        "malformed_model_response",
    }
    selected = [next(case for case in cases if case.category == category) for category in critical]
    results = [runner._run_case(case) for case in selected]

    assert all(result.success for result in results)
