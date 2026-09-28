"""RetailAnalystBench: deterministic end-to-end BA Agent evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from time import perf_counter

from eiw.retail.models import RetailAnalysisRequest
from eiw.retail.runtime import RetailBARuntime


@dataclass(frozen=True)
class RetailBenchmarkCase:
    case_id: str
    question: str
    expected_driver_terms: tuple[str, ...]
    required_sections: tuple[str, ...] = (
        "business-performance",
        "diagnostics",
        "promotion-merchandising",
    )


@dataclass(frozen=True)
class RetailBenchmarkResult:
    case_id: str
    driver_recall_at_k: float
    report_completeness: float
    has_action: float
    elapsed_ms: float


DEFAULT_CASES = (
    RetailBenchmarkCase(
        case_id="retail-decline-diagnosis",
        question="Why did recent sales decline and what should management do next?",
        expected_driver_terms=("3", "4", "SUN CARE"),
    ),
    RetailBenchmarkCase(
        case_id="retail-merchandising",
        question="Analyze recent promotion and display performance and identify the biggest opportunities.",
        expected_driver_terms=("FRONT END CAP",),
    ),
)


class RetailBenchmarkRunner:
    def __init__(self, runtime: RetailBARuntime) -> None:
        self.runtime = runtime

    def run(self, cases: tuple[RetailBenchmarkCase, ...] = DEFAULT_CASES) -> dict[str, object]:
        results: list[RetailBenchmarkResult] = []
        for case in cases:
            started = perf_counter()
            response = self.runtime.analyze(RetailAnalysisRequest(question=case.question, top_k=10))
            elapsed_ms = (perf_counter() - started) * 1000.0
            haystack = " ".join(
                [
                    *(insight.title for insight in response.insights[:10]),
                    *(insight.finding for insight in response.insights[:10]),
                ]
            ).upper()
            matched = sum(1 for term in case.expected_driver_terms if term.upper() in haystack)
            recall = matched / len(case.expected_driver_terms) if case.expected_driver_terms else 1.0
            sections = {section["id"] for section in response.report.sections}
            completeness = sum(1 for section in case.required_sections if section in sections) / len(case.required_sections)
            results.append(
                RetailBenchmarkResult(
                    case_id=case.case_id,
                    driver_recall_at_k=recall,
                    report_completeness=completeness,
                    has_action=1.0 if response.report.actions else 0.0,
                    elapsed_ms=elapsed_ms,
                )
            )

        return {
            "suite": "RetailAnalystBench-smoke-v1",
            "cases": len(results),
            "driver_recall_at_k": fmean(result.driver_recall_at_k for result in results),
            "report_completeness": fmean(result.report_completeness for result in results),
            "action_coverage": fmean(result.has_action for result in results),
            "mean_elapsed_ms": fmean(result.elapsed_ms for result in results),
            "results": [result.__dict__ for result in results],
        }
