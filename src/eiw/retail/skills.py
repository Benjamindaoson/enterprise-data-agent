"""Typed analytical worker implementations for the retail BA Agent."""

from __future__ import annotations

from collections.abc import Callable

from eiw.retail.data import RetailDataEngine
from eiw.retail.models import WorkstreamName, WorkstreamResult


class RetailAnalyticalWorkers:
    def __init__(self, data: RetailDataEngine) -> None:
        self.data = data
        self._handlers: dict[
            WorkstreamName,
            Callable[[list[int], list[int]], WorkstreamResult],
        ] = {
            WorkstreamName.OVERVIEW: self.overview,
            WorkstreamName.STORE: self.store,
            WorkstreamName.PRODUCT: self.product,
            WorkstreamName.PROMOTION: self.promotion,
            WorkstreamName.CUSTOMER: self.customer,
        }

    def run(
        self,
        name: WorkstreamName,
        current: list[int],
        previous: list[int],
    ) -> WorkstreamResult:
        return self._handlers[name](current, previous)

    def overview(self, current: list[int], previous: list[int]) -> WorkstreamResult:
        metrics = self.data.overview(current, previous)
        direction = "down" if float(metrics["sales_change_pct"]) < 0 else "up"
        return WorkstreamResult(
            name=WorkstreamName.OVERVIEW,
            summary=f"Sales are {direction} {abs(float(metrics['sales_change_pct'])):.1f}% versus the comparison period.",
            metrics=metrics,
        )

    def store(self, current: list[int], previous: list[int]) -> WorkstreamResult:
        rows = self.data.contribution("store", current, previous, limit=12)
        anomalies = self.data.store_anomalies(current, limit=8)
        worst = next((row for row in rows if float(row["delta"]) < 0), rows[0] if rows else None)
        summary = (
            f"Store {worst['segment']} is the largest listed negative contributor."
            if worst
            else "No store contribution was available."
        )
        cross_scan = self.data.cross_dimension_scan(current, previous, limit=20)
        return WorkstreamResult(
            name=WorkstreamName.STORE,
            summary=summary,
            rows=rows,
            artifacts=[
                {"type": "store_anomalies", "rows": anomalies},
                {"type": "store_commodity_scan", "rows": cross_scan},
            ],
        )

    def product(self, current: list[int], previous: list[int]) -> WorkstreamResult:
        rows = self.data.contribution("commodity", current, previous, limit=12)
        worst = next((row for row in rows if float(row["delta"]) < 0), rows[0] if rows else None)
        summary = (
            f"{worst['segment']} is the largest listed commodity driver."
            if worst
            else "No product contribution was available."
        )
        price_volume = self.data.price_volume_decomposition(current, previous, limit=12)
        return WorkstreamResult(
            name=WorkstreamName.PRODUCT,
            summary=summary,
            rows=rows,
            artifacts=[{"type": "price_volume_decomposition", "rows": price_volume}],
        )

    def promotion(self, current: list[int], previous: list[int]) -> WorkstreamResult:
        rows = self.data.promotion_performance(current, limit=12)
        summary = (
            f"{rows[0]['display_location']} has the highest observed sales among display states."
            if rows
            else "No promotion or merchandising observations were available."
        )
        return WorkstreamResult(
            name=WorkstreamName.PROMOTION,
            summary=summary,
            rows=rows,
        )

    def customer(self, current: list[int], previous: list[int]) -> WorkstreamResult:
        customers = self.data.customer_segments(current, limit=10)
        pairs = self.data.basket_affinity(current, limit=10)
        summary = (
            f"Top customer generated {float(customers[0]['sales']):.1f} sales in the analysis window."
            if customers
            else "No customer observations were available."
        )
        return WorkstreamResult(
            name=WorkstreamName.CUSTOMER,
            summary=summary,
            rows=customers,
            artifacts=[{"type": "basket_affinity", "rows": pairs}],
        )
