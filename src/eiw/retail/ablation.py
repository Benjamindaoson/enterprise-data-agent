"""Ablation evaluation for BA Agent harness choices.

This benchmark keeps the same underlying analytical workstream outputs and
changes only selection/orchestration behavior. It is designed to answer a
resume/interview-relevant question: how much value comes from the agent
harness, not merely from the raw analytical operators?
"""

from __future__ import annotations

from statistics import fmean
from time import perf_counter

from eiw.retail.benchmark import RetailBenchmarkCase, RetailBenchmarkRunner
from eiw.retail.insight import InsightMiner
from eiw.retail.models import RetailAnalysisRequest, WorkstreamName
from eiw.retail.planner import InvestigationPlanner
from eiw.retail.runtime import RetailBARuntime
from eiw.retail.team import RetailAnalysisTeam


def _driver_recall(case: RetailBenchmarkCase, insights: list) -> float:
    if not case.expected_driver_terms:
        return 1.0
    haystack = " ".join(
        [
            *(item.title for item in insights),
            *(item.finding for item in insights),
            *(item.business_impact for item in insights),
        ]
    ).upper()
    matched = sum(
        1
        for term in case.expected_driver_terms
        if term.upper() in haystack
    )
    return matched / len(case.expected_driver_terms)


class RetailHarnessAblationRunner:
    def __init__(self, runtime: RetailBARuntime) -> None:
        self.runtime = runtime
        self.benchmark = RetailBenchmarkRunner(runtime)

    def run(self) -> dict[str, object]:
        cases = self.benchmark.build_cases()
        current, previous = self.runtime.data.week_bounds()
        naive_recalls: list[float] = []
        query_aware_recalls: list[float] = []
        initial_counts: list[int] = []
        final_counts: list[int] = []
        cases_with_replan = 0
        case_rows: list[dict[str, object]] = []

        for case in cases:
            request = RetailAnalysisRequest(
                question=case.question,
                current_weeks=current,
                previous_weeks=previous,
                top_k=10,
            )
            response = self.runtime.analyze(request)

            # Naive baseline: same completed workstreams, but rank only by the
            # intrinsic insight score and ignore resolved business semantics.
            naive = InsightMiner().mine(
                response.workstreams,
                top_k=10,
                context=None,
            )
            naive_recall = _driver_recall(case, naive)
            aware_recall = _driver_recall(case, response.insights)

            planner = InvestigationPlanner()
            initial = planner.initial_plan(request)
            final_names = [item.name for item in response.workstreams]
            added = [name for name in final_names if name not in initial]
            if added:
                cases_with_replan += 1

            naive_recalls.append(naive_recall)
            query_aware_recalls.append(aware_recall)
            initial_counts.append(len(initial))
            final_counts.append(len(final_names))
            case_rows.append(
                {
                    "case_id": case.case_id,
                    "intrinsic_rank_driver_recall_at_k": naive_recall,
                    "query_aware_driver_recall_at_k": aware_recall,
                    "initial_workstreams": [item.value for item in initial],
                    "final_workstreams": [item.value for item in final_names],
                    "replan_added": [item.value for item in added],
                }
            )

        speed = self._parallel_speed(current, previous)
        intrinsic = fmean(naive_recalls)
        aware = fmean(query_aware_recalls)
        return {
            "suite": "RetailHarnessAblation-v1",
            "cases": len(cases),
            "comparison": "same analytical outputs; harness selection/orchestration ablation",
            "intrinsic_rank_driver_recall_at_k": intrinsic,
            "query_aware_driver_recall_at_k": aware,
            "driver_recall_gain_pp": (aware - intrinsic) * 100.0,
            "cases_with_replan": cases_with_replan,
            "mean_initial_workstreams": fmean(initial_counts),
            "mean_final_workstreams": fmean(final_counts),
            "parallel_execution": speed,
            "results": case_rows,
        }

    def _parallel_speed(
        self,
        current: list[int],
        previous: list[int],
    ) -> dict[str, float]:
        names = [
            WorkstreamName.OVERVIEW,
            WorkstreamName.STORE,
            WorkstreamName.PRODUCT,
            WorkstreamName.PROMOTION,
            WorkstreamName.CUSTOMER,
        ]
        workers = self.runtime.workers
        team = RetailAnalysisTeam(workers)

        # Warm both paths once so parser/data-page cache effects are not
        # attributed to concurrency.
        for name in names:
            workers.run(name, current, previous)
        team.run_wave(names, current, previous)

        sequential_samples: list[float] = []
        parallel_samples: list[float] = []
        for _ in range(3):
            started = perf_counter()
            for name in names:
                workers.run(name, current, previous)
            sequential_samples.append((perf_counter() - started) * 1000.0)

            started = perf_counter()
            team.run_wave(names, current, previous)
            parallel_samples.append((perf_counter() - started) * 1000.0)

        sequential_ms = fmean(sequential_samples)
        parallel_ms = fmean(parallel_samples)
        return {
            "sequential_mean_ms": sequential_ms,
            "parallel_mean_ms": parallel_ms,
            "wall_clock_speedup": (
                sequential_ms / parallel_ms if parallel_ms > 0 else 0.0
            ),
        }
