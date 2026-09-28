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
    expected_driver_terms: tuple[str, ...] = ()
    expected_metrics: tuple[str, ...] = ()
    expected_dimensions: tuple[str, ...] = ()
    expected_intents: tuple[str, ...] = ()
    required_sections: tuple[str, ...] = (
        "business-performance",
        "diagnostics",
        "promotion-merchandising",
    )


@dataclass(frozen=True)
class RetailBenchmarkResult:
    case_id: str
    driver_recall_at_k: float
    semantic_coverage: float
    numeric_accuracy: float
    report_completeness: float
    has_action: float
    time_to_first_insight_ms: float
    elapsed_ms: float


class RetailBenchmarkRunner:
    def __init__(self, runtime: RetailBARuntime) -> None:
        self.runtime = runtime

    def build_cases(self) -> tuple[RetailBenchmarkCase, ...]:
        current, previous = self.runtime.data.week_bounds()
        store_rows = self.runtime.data.contribution("store", current, previous, limit=10)
        commodity_rows = self.runtime.data.contribution("commodity", current, previous, limit=10)
        cross_rows = self.runtime.data.cross_dimension_scan(current, previous, limit=20)
        display_rows = self.runtime.data.promotion_performance(current, limit=10)

        def first_negative(rows: list[dict[str, object]], key: str) -> str | None:
            for row in rows:
                delta = float(row.get("delta", row.get("sales_delta", 0.0)) or 0.0)
                if delta < 0:
                    return str(row[key])
            return None

        store = first_negative(store_rows, "segment")
        commodity = first_negative(commodity_rows, "segment")
        cross = next(
            (
                row
                for row in cross_rows
                if float(row.get("sales_delta") or 0.0) < 0
            ),
            None,
        )
        display = str(display_rows[0]["display_location"]) if display_rows else None

        driver_terms = tuple(
            value
            for value in (
                store,
                commodity,
                str(cross["store_id"]) if cross else None,
                str(cross["commodity"]) if cross else None,
            )
            if value
        )

        return (
            RetailBenchmarkCase(
                case_id="retail-decline-diagnosis",
                question="Why did recent sales decline and what should management do next?",
                expected_driver_terms=driver_terms,
                expected_metrics=("sales_value",),
                expected_dimensions=("store", "commodity"),
                expected_intents=("diagnose", "recommend"),
            ),
            RetailBenchmarkCase(
                case_id="retail-merchandising",
                question="Analyze recent promotion and display performance and identify the biggest opportunities.",
                expected_driver_terms=(display,) if display else (),
                expected_metrics=("discount_amount",),
                expected_dimensions=("display",),
                expected_intents=("discover",),
            ),
            RetailBenchmarkCase(
                case_id="retail-executive-review",
                question="Prepare a business report on recent sales performance, key drivers and next actions.",
                expected_driver_terms=tuple(value for value in (store, commodity) if value),
                expected_metrics=("sales_value",),
                expected_dimensions=("store", "commodity", "week"),
                expected_intents=("report", "recommend"),
            ),
        )

    def run(
        self,
        cases: tuple[RetailBenchmarkCase, ...] | None = None,
    ) -> dict[str, object]:
        current, previous = self.runtime.data.week_bounds()
        gold_kpis = self.runtime.data.overview(current, previous)
        suite = cases or self.build_cases()
        results: list[RetailBenchmarkResult] = []

        for case in suite:
            started = perf_counter()
            response = self.runtime.analyze(
                RetailAnalysisRequest(
                    question=case.question,
                    current_weeks=current,
                    previous_weeks=previous,
                    top_k=10,
                )
            )
            elapsed_ms = (perf_counter() - started) * 1000.0
            haystack = " ".join(
                [
                    *(insight.title for insight in response.insights[:10]),
                    *(insight.finding for insight in response.insights[:10]),
                    *(insight.business_impact for insight in response.insights[:10]),
                ]
            ).upper()
            matched = sum(
                1
                for term in case.expected_driver_terms
                if term.upper() in haystack
            )
            recall = (
                matched / len(case.expected_driver_terms)
                if case.expected_driver_terms
                else 1.0
            )

            expected_semantics = [
                *(("metric", value) for value in case.expected_metrics),
                *(("dimension", value) for value in case.expected_dimensions),
                *(("intent", value) for value in case.expected_intents),
            ]
            semantic_hits = 0
            for kind, value in expected_semantics:
                matched = (
                    (kind == "metric" and value in response.semantics.metrics)
                    or (kind == "dimension" and value in response.semantics.dimensions)
                    or (kind == "intent" and value in response.semantics.intents)
                )
                if matched:
                    semantic_hits += 1
            semantic_coverage = (
                semantic_hits / len(expected_semantics)
                if expected_semantics
                else 1.0
            )

            numeric_checks = []
            for key in (
                "current_sales",
                "previous_sales",
                "current_units",
                "current_baskets",
                "sales_change_pct",
            ):
                actual = float(response.kpis.get(key) or 0.0)
                expected = float(gold_kpis.get(key) or 0.0)
                tolerance = max(1e-8, abs(expected) * 1e-9)
                numeric_checks.append(abs(actual - expected) <= tolerance)
            numeric_accuracy = sum(numeric_checks) / len(numeric_checks)

            sections = {section["id"] for section in response.report.sections}
            completeness = (
                sum(
                    1
                    for section in case.required_sections
                    if section in sections
                )
                / len(case.required_sections)
            )

            first_insight = next(
                (
                    event.elapsed_ms
                    for event in response.events
                    if event.event_type == "insight_discovered"
                    and event.elapsed_ms is not None
                ),
                elapsed_ms,
            )

            results.append(
                RetailBenchmarkResult(
                    case_id=case.case_id,
                    driver_recall_at_k=recall,
                    semantic_coverage=semantic_coverage,
                    numeric_accuracy=numeric_accuracy,
                    report_completeness=completeness,
                    has_action=1.0 if response.report.actions else 0.0,
                    time_to_first_insight_ms=float(first_insight),
                    elapsed_ms=elapsed_ms,
                )
            )

        ordered_elapsed = sorted(result.elapsed_ms for result in results)
        p95_index = min(
            len(ordered_elapsed) - 1,
            max(0, round((len(ordered_elapsed) - 1) * 0.95)),
        )
        return {
            "suite": "RetailAnalystBench-smoke-v2",
            "cases": len(results),
            "driver_recall_at_k": fmean(
                result.driver_recall_at_k for result in results
            ),
            "semantic_coverage": fmean(
                result.semantic_coverage for result in results
            ),
            "numeric_accuracy": fmean(
                result.numeric_accuracy for result in results
            ),
            "report_completeness": fmean(
                result.report_completeness for result in results
            ),
            "action_coverage": fmean(result.has_action for result in results),
            "mean_time_to_first_insight_ms": fmean(
                result.time_to_first_insight_ms for result in results
            ),
            "mean_elapsed_ms": fmean(result.elapsed_ms for result in results),
            "p95_elapsed_ms": ordered_elapsed[p95_index],
            "results": [result.__dict__ for result in results],
        }
