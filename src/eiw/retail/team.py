"""Parallel specialist-team execution for retail business analysis."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from eiw.retail.models import WorkstreamName, WorkstreamResult
from eiw.retail.skills import RetailAnalyticalWorkers


@dataclass(frozen=True)
class SpecialistProfile:
    name: str
    workstream: WorkstreamName
    mission: str


DEFAULT_SPECIALISTS = {
    WorkstreamName.OVERVIEW: SpecialistProfile(
        name="Performance Analyst",
        workstream=WorkstreamName.OVERVIEW,
        mission="Establish the KPI baseline and quantify the business movement.",
    ),
    WorkstreamName.STORE: SpecialistProfile(
        name="Store Analyst",
        workstream=WorkstreamName.STORE,
        mission="Find store-level contributors, exceptions and drill-down targets.",
    ),
    WorkstreamName.PRODUCT: SpecialistProfile(
        name="Product Analyst",
        workstream=WorkstreamName.PRODUCT,
        mission="Find category, commodity and product drivers.",
    ),
    WorkstreamName.PROMOTION: SpecialistProfile(
        name="Promotion & Merchandising Analyst",
        workstream=WorkstreamName.PROMOTION,
        mission="Evaluate promotion and merchandising associations without causal overclaim.",
    ),
    WorkstreamName.CUSTOMER: SpecialistProfile(
        name="Customer & Basket Analyst",
        workstream=WorkstreamName.CUSTOMER,
        mission="Inspect customer concentration and basket relationships.",
    ),
}


class RetailAnalysisTeam:
    """Executes specialist analytical workers concurrently.

    Workers share typed data contracts, not hidden model reasoning. The supervisor
    may launch additional waves after observing intermediate results.
    """

    def __init__(self, workers: RetailAnalyticalWorkers) -> None:
        self.workers = workers

    def run_wave(
        self,
        names: list[WorkstreamName],
        current: list[int],
        previous: list[int],
        *,
        on_started: Callable[[SpecialistProfile], None] | None = None,
        on_completed: Callable[[SpecialistProfile, WorkstreamResult], None] | None = None,
    ) -> list[WorkstreamResult]:
        if not names:
            return []
        results: list[WorkstreamResult] = []
        with ThreadPoolExecutor(max_workers=len(names)) as executor:
            futures = {}
            for name in names:
                profile = DEFAULT_SPECIALISTS[name]
                if on_started:
                    on_started(profile)
                futures[executor.submit(self.workers.run, name, current, previous)] = profile

            for future in as_completed(futures):
                profile = futures[future]
                result = future.result()
                results.append(result)
                if on_completed:
                    on_completed(profile, result)

        order = {name: index for index, name in enumerate(names)}
        return sorted(results, key=lambda item: order[item.name])
