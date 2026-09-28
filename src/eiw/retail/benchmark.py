"""RetailAnalystBench: end-to-end BA Agent evaluation with independent SQL gold."""

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
    required_sections: tuple[str, ...] = ("business-performance",)
    current_weeks: tuple[int, ...] = ()
    previous_weeks: tuple[int, ...] = ()


@dataclass(frozen=True)
class RetailBenchmarkResult:
    case_id: str
    driver_recall_at_k: float
    expected_driver_terms: tuple[str, ...]
    matched_driver_terms: tuple[str, ...]
    semantic_coverage: float
    missing_semantics: tuple[str, ...]
    numeric_accuracy: float
    report_completeness: float
    has_action: float
    replanned: float
    time_to_first_insight_ms: float
    elapsed_ms: float


class RetailBenchmarkRunner:
    """Evaluate the BA runtime against independently computed deterministic gold.

    Gold KPI and driver values are calculated with direct SQL over normalized
    retail views, rather than by calling the same typed analytical methods used
    by the Agent workers.
    """

    def __init__(self, runtime: RetailBARuntime) -> None:
        self.runtime = runtime

    @staticmethod
    def _marks(values: list[int]) -> str:
        if not values:
            raise ValueError("benchmark week window must not be empty")
        return ", ".join("?" for _ in values)

    def _gold_kpis(
        self,
        current: list[int],
        previous: list[int],
    ) -> dict[str, float]:
        current_marks = self._marks(current)
        previous_marks = self._marks(previous)
        row = self.runtime.data.query_readonly(
            f"""
            WITH current_period AS (
                SELECT
                    SUM(sales_value) AS sales,
                    SUM(quantity) AS units,
                    COUNT(DISTINCT basket_id) AS baskets
                FROM retail_transactions
                WHERE week_no IN ({current_marks})
            ),
            previous_period AS (
                SELECT
                    SUM(sales_value) AS sales,
                    SUM(quantity) AS units,
                    COUNT(DISTINCT basket_id) AS baskets
                FROM retail_transactions
                WHERE week_no IN ({previous_marks})
            )
            SELECT
                current_period.sales AS current_sales,
                previous_period.sales AS previous_sales,
                current_period.units AS current_units,
                previous_period.units AS previous_units,
                current_period.baskets AS current_baskets,
                previous_period.baskets AS previous_baskets
            FROM current_period, previous_period
            """,
            [*current, *previous],
        )[0]

        current_sales = float(row["current_sales"] or 0.0)
        previous_sales = float(row["previous_sales"] or 0.0)
        current_units = float(row["current_units"] or 0.0)
        previous_units = float(row["previous_units"] or 0.0)
        current_baskets = float(row["current_baskets"] or 0.0)
        previous_baskets = float(row["previous_baskets"] or 0.0)

        def change(current_value: float, previous_value: float) -> float:
            if not previous_value:
                return 0.0
            return (current_value - previous_value) / previous_value * 100.0

        return {
            "current_sales": current_sales,
            "previous_sales": previous_sales,
            "current_units": current_units,
            "current_baskets": current_baskets,
            "sales_change_pct": change(current_sales, previous_sales),
            "units_change_pct": change(current_units, previous_units),
            "basket_change_pct": change(current_baskets, previous_baskets),
            "avg_basket_value": (
                current_sales / current_baskets if current_baskets else 0.0
            ),
        }

    def _gold_contribution(
        self,
        dimension: str,
        current: list[int],
        previous: list[int],
    ) -> list[dict[str, object]]:
        current_marks = self._marks(current)
        previous_marks = self._marks(previous)
        if dimension == "store":
            expression = "CAST(t.store_id AS VARCHAR)"
            join = ""
        elif dimension == "commodity":
            expression = "p.commodity"
            join = "JOIN retail_products p ON p.product_id = t.product_id"
        else:
            raise ValueError(dimension)

        return self.runtime.data.query_readonly(
            f"""
            WITH current_period AS (
                SELECT {expression} AS segment, SUM(t.sales_value) AS value
                FROM retail_transactions t
                {join}
                WHERE t.week_no IN ({current_marks})
                GROUP BY 1
            ),
            previous_period AS (
                SELECT {expression} AS segment, SUM(t.sales_value) AS value
                FROM retail_transactions t
                {join}
                WHERE t.week_no IN ({previous_marks})
                GROUP BY 1
            )
            SELECT
                COALESCE(current_period.segment, previous_period.segment) AS segment,
                COALESCE(current_period.value, 0) - COALESCE(previous_period.value, 0) AS delta
            FROM current_period
            FULL OUTER JOIN previous_period USING(segment)
            ORDER BY ABS(delta) DESC
            LIMIT 12
            """,
            [*current, *previous],
        )

    def _gold_cross_driver(
        self,
        current: list[int],
        previous: list[int],
    ) -> dict[str, object] | None:
        current_marks = self._marks(current)
        previous_marks = self._marks(previous)
        rows = self.runtime.data.query_readonly(
            f"""
            WITH current_period AS (
                SELECT
                    t.store_id,
                    p.commodity,
                    SUM(t.sales_value) AS sales
                FROM retail_transactions t
                JOIN retail_products p ON p.product_id = t.product_id
                WHERE t.week_no IN ({current_marks})
                GROUP BY 1, 2
            ),
            previous_period AS (
                SELECT
                    t.store_id,
                    p.commodity,
                    SUM(t.sales_value) AS sales
                FROM retail_transactions t
                JOIN retail_products p ON p.product_id = t.product_id
                WHERE t.week_no IN ({previous_marks})
                GROUP BY 1, 2
            )
            SELECT
                COALESCE(current_period.store_id, previous_period.store_id) AS store_id,
                COALESCE(current_period.commodity, previous_period.commodity) AS commodity,
                COALESCE(current_period.sales, 0) - COALESCE(previous_period.sales, 0) AS delta
            FROM current_period
            FULL OUTER JOIN previous_period USING(store_id, commodity)
            WHERE COALESCE(current_period.sales, 0) - COALESCE(previous_period.sales, 0) < 0
            ORDER BY ABS(delta) DESC
            LIMIT 1
            """,
            [*current, *previous],
        )
        return rows[0] if rows else None

    def _gold_display(self, current: list[int]) -> str | None:
        marks = self._marks(current)
        rows = self.runtime.data.query_readonly(
            f"""
            SELECT
                COALESCE(NULLIF(TRIM(p.display_location), ''), 'UNKNOWN') AS display_location,
                AVG(t.sales_value) AS avg_line_sales
            FROM retail_transactions t
            JOIN retail_promotions p
              ON p.product_id = t.product_id
             AND p.store_id = t.store_id
             AND p.week_no = t.week_no
            WHERE t.week_no IN ({marks})
            GROUP BY 1
            ORDER BY avg_line_sales DESC
            LIMIT 1
            """,
            current,
        )
        return str(rows[0]["display_location"]) if rows else None

    @staticmethod
    def _first_negative(
        rows: list[dict[str, object]],
    ) -> str | None:
        for row in rows:
            if float(row.get("delta") or 0.0) < 0:
                return str(row["segment"])
        return str(rows[0]["segment"]) if rows else None

    def build_cases(self) -> tuple[RetailBenchmarkCase, ...]:
        current, previous = self.runtime.data.week_bounds()
        store_rows = self._gold_contribution("store", current, previous)
        commodity_rows = self._gold_contribution("commodity", current, previous)
        negative_store = self._first_negative(store_rows)
        negative_commodity = self._first_negative(commodity_rows)
        top_store = str(store_rows[0]["segment"]) if store_rows else None
        top_commodity = str(commodity_rows[0]["segment"]) if commodity_rows else None
        cross = self._gold_cross_driver(current, previous)
        display = self._gold_display(current)

        return (
            RetailBenchmarkCase(
                case_id="retail-kpi-summary",
                question=(
                    "Summarize recent sales, units, baskets and average basket value "
                    "as a management report."
                ),
                expected_metrics=(
                    "sales_value",
                    "units",
                    "baskets",
                    "average_basket_value",
                ),
                expected_dimensions=("week",),
                expected_intents=("report",),
            ),
            RetailBenchmarkCase(
                case_id="retail-decline-diagnosis",
                question=(
                    "Why did recent sales decline and what should management do next?"
                ),
                expected_driver_terms=tuple(
                    value
                    for value in (negative_store, negative_commodity)
                    if value
                ),
                expected_metrics=("sales_value",),
                expected_dimensions=("store", "commodity", "week"),
                expected_intents=("diagnose", "recommend"),
                required_sections=("business-performance", "diagnostics"),
            ),
            RetailBenchmarkCase(
                case_id="retail-store-drivers",
                question="Why did recent sales change by store? Identify the biggest drivers.",
                expected_driver_terms=(top_store,) if top_store else (),
                expected_metrics=("sales_value",),
                expected_dimensions=("store", "commodity", "week"),
                expected_intents=("diagnose",),
                required_sections=("business-performance", "diagnostics"),
            ),
            RetailBenchmarkCase(
                case_id="retail-product-drivers",
                question=(
                    "Why did recent sales change by category? Identify the largest "
                    "commodity drivers."
                ),
                expected_driver_terms=(top_commodity,) if top_commodity else (),
                expected_metrics=("sales_value",),
                expected_dimensions=("commodity", "store", "week"),
                expected_intents=("diagnose",),
                required_sections=("business-performance", "diagnostics"),
            ),
            RetailBenchmarkCase(
                case_id="retail-cross-dimension",
                question=(
                    "Find the largest recent store and category anomaly and explain "
                    "where management should drill down."
                ),
                expected_driver_terms=tuple(
                    value
                    for value in (
                        str(cross["store_id"]) if cross else None,
                        str(cross["commodity"]) if cross else None,
                    )
                    if value
                ),
                expected_metrics=("sales_value",),
                expected_dimensions=("store", "commodity", "week"),
                expected_intents=("discover",),
                required_sections=("business-performance", "diagnostics"),
            ),
            RetailBenchmarkCase(
                case_id="retail-price-volume",
                question=(
                    "Decompose recent sales change into price and volume by category "
                    "and recommend the next action."
                ),
                expected_driver_terms=(top_commodity,) if top_commodity else (),
                expected_metrics=("sales_value", "units"),
                expected_dimensions=("commodity", "week"),
                expected_intents=("decompose", "recommend"),
                required_sections=("business-performance", "diagnostics"),
            ),
            RetailBenchmarkCase(
                case_id="retail-merchandising",
                question=(
                    "Analyze recent promotion and display performance and identify "
                    "the biggest opportunities."
                ),
                expected_driver_terms=(display,) if display else (),
                expected_metrics=("discount_amount",),
                expected_dimensions=("display", "store", "commodity", "week"),
                expected_intents=("discover",),
                required_sections=(
                    "business-performance",
                    "promotion-merchandising",
                ),
            ),
            RetailBenchmarkCase(
                case_id="retail-customer-basket",
                question=(
                    "Find customer and basket opportunities in the recent period "
                    "and recommend what to investigate next."
                ),
                expected_metrics=("baskets",),
                expected_dimensions=("household", "store", "commodity"),
                expected_intents=("discover", "recommend"),
                required_sections=("business-performance", "customer-basket"),
            ),
            RetailBenchmarkCase(
                case_id="retail-customer-income",
                question=(
                    "Find customer income segment sales opportunities and explain "
                    "the largest observed sales movement."
                ),
                expected_metrics=("sales_value",),
                expected_dimensions=("income", "store", "commodity"),
                expected_intents=("discover",),
                required_sections=("business-performance", "customer-basket"),
            ),
            RetailBenchmarkCase(
                case_id="retail-executive-review",
                question=(
                    "Prepare a report on recent sales performance, key store and "
                    "category drivers, and recommend next actions."
                ),
                expected_driver_terms=tuple(
                    value for value in (top_store, top_commodity) if value
                ),
                expected_metrics=("sales_value",),
                expected_dimensions=("store", "commodity", "week"),
                expected_intents=("report", "recommend"),
                required_sections=(
                    "business-performance",
                    "diagnostics",
                    "promotion-merchandising",
                    "customer-basket",
                ),
            ),
        )

    def build_rolling_cases(
        self,
        *,
        windows: int = 5,
    ) -> tuple[RetailBenchmarkCase, ...]:
        """Build repeated BA cases across historical week windows."""

        week_rows = self.runtime.data.query_readonly(
            "SELECT DISTINCT week_no FROM retail_transactions ORDER BY week_no"
        )
        weeks = [int(row["week_no"]) for row in week_rows]
        if len(weeks) < 4:
            return ()

        candidate_indexes = list(range(3, len(weeks)))
        target = min(windows, len(candidate_indexes))
        if target == 1:
            selected_indexes = [candidate_indexes[-1]]
        else:
            selected_indexes = sorted(
                {
                    candidate_indexes[
                        round(position * (len(candidate_indexes) - 1) / (target - 1))
                    ]
                    for position in range(target)
                }
            )

        cases: list[RetailBenchmarkCase] = []
        for window_index, idx in enumerate(selected_indexes, start=1):
            current = [weeks[idx - 1], weeks[idx]]
            previous = [weeks[idx - 3], weeks[idx - 2]]
            store_rows = self._gold_contribution("store", current, previous)
            commodity_rows = self._gold_contribution(
                "commodity",
                current,
                previous,
            )
            top_store = (
                str(store_rows[0]["segment"]) if store_rows else None
            )
            top_commodity = (
                str(commodity_rows[0]["segment"]) if commodity_rows else None
            )
            cross = self._gold_cross_driver(current, previous)
            suffix = f"w{window_index}-{current[-1]}"
            common = {
                "current_weeks": tuple(current),
                "previous_weeks": tuple(previous),
            }

            cases.extend(
                [
                    RetailBenchmarkCase(
                        case_id=f"rolling-kpi-{suffix}",
                        question=(
                            "Summarize recent sales, units, baskets and average "
                            "basket value as a management report."
                        ),
                        expected_metrics=(
                            "sales_value",
                            "units",
                            "baskets",
                            "average_basket_value",
                        ),
                        expected_dimensions=("week",),
                        expected_intents=("report",),
                        **common,
                    ),
                    RetailBenchmarkCase(
                        case_id=f"rolling-store-{suffix}",
                        question=(
                            "Why did recent sales change by store? Identify the "
                            "biggest drivers."
                        ),
                        expected_driver_terms=(
                            (top_store,) if top_store else ()
                        ),
                        expected_metrics=("sales_value",),
                        expected_dimensions=("store", "commodity", "week"),
                        expected_intents=("diagnose",),
                        required_sections=(
                            "business-performance",
                            "diagnostics",
                        ),
                        **common,
                    ),
                    RetailBenchmarkCase(
                        case_id=f"rolling-product-{suffix}",
                        question=(
                            "Why did recent sales change by category? Identify "
                            "the largest commodity drivers."
                        ),
                        expected_driver_terms=(
                            (top_commodity,) if top_commodity else ()
                        ),
                        expected_metrics=("sales_value",),
                        expected_dimensions=("commodity", "store", "week"),
                        expected_intents=("diagnose",),
                        required_sections=(
                            "business-performance",
                            "diagnostics",
                        ),
                        **common,
                    ),
                    RetailBenchmarkCase(
                        case_id=f"rolling-cross-{suffix}",
                        question=(
                            "Find the largest recent store and category anomaly "
                            "and explain where management should drill down."
                        ),
                        expected_driver_terms=tuple(
                            value
                            for value in (
                                str(cross["store_id"]) if cross else None,
                                str(cross["commodity"]) if cross else None,
                            )
                            if value
                        ),
                        expected_metrics=("sales_value",),
                        expected_dimensions=("store", "commodity", "week"),
                        expected_intents=("discover",),
                        required_sections=(
                            "business-performance",
                            "diagnostics",
                        ),
                        **common,
                    ),
                    RetailBenchmarkCase(
                        case_id=f"rolling-pv-{suffix}",
                        question=(
                            "Decompose recent sales change into price and volume "
                            "by category and recommend the next action."
                        ),
                        expected_driver_terms=(
                            (top_commodity,) if top_commodity else ()
                        ),
                        expected_metrics=("sales_value", "units"),
                        expected_dimensions=("commodity", "week"),
                        expected_intents=("decompose", "recommend"),
                        required_sections=(
                            "business-performance",
                            "diagnostics",
                        ),
                        **common,
                    ),
                    RetailBenchmarkCase(
                        case_id=f"rolling-review-{suffix}",
                        question=(
                            "Prepare a report on recent sales performance, key "
                            "store and category drivers, and recommend next actions."
                        ),
                        expected_driver_terms=tuple(
                            value
                            for value in (top_store, top_commodity)
                            if value
                        ),
                        expected_metrics=("sales_value",),
                        expected_dimensions=("store", "commodity", "week"),
                        expected_intents=("report", "recommend"),
                        required_sections=(
                            "business-performance",
                            "diagnostics",
                            "promotion-merchandising",
                            "customer-basket",
                        ),
                        **common,
                    ),
                ]
            )
        return tuple(cases)

    def run(
        self,
        cases: tuple[RetailBenchmarkCase, ...] | None = None,
    ) -> dict[str, object]:
        default_current, default_previous = self.runtime.data.week_bounds()
        suite = cases or self.build_cases()
        results: list[RetailBenchmarkResult] = []

        for case in suite:
            current = (
                list(case.current_weeks)
                if case.current_weeks
                else default_current
            )
            previous = (
                list(case.previous_weeks)
                if case.previous_weeks
                else default_previous
            )
            gold_kpis = self._gold_kpis(current, previous)
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
            matched_driver_terms = tuple(
                term
                for term in case.expected_driver_terms
                if term.upper() in haystack
            )
            matched = len(matched_driver_terms)
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
            missing_semantics: list[str] = []
            for kind, value in expected_semantics:
                matched_semantic = (
                    (kind == "metric" and value in response.semantics.metrics)
                    or (
                        kind == "dimension"
                        and value in response.semantics.dimensions
                    )
                    or (kind == "intent" and value in response.semantics.intents)
                )
                if matched_semantic:
                    semantic_hits += 1
                else:
                    missing_semantics.append(f"{kind}:{value}")
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
                "units_change_pct",
                "basket_change_pct",
                "avg_basket_value",
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
                    expected_driver_terms=case.expected_driver_terms,
                    matched_driver_terms=matched_driver_terms,
                    semantic_coverage=semantic_coverage,
                    missing_semantics=tuple(missing_semantics),
                    numeric_accuracy=numeric_accuracy,
                    report_completeness=completeness,
                    has_action=1.0 if response.report.actions else 0.0,
                    replanned=(
                        1.0
                        if any(
                            event.event_type == "replan_ready"
                            for event in response.events
                        )
                        else 0.0
                    ),
                    time_to_first_insight_ms=float(first_insight),
                    elapsed_ms=elapsed_ms,
                )
            )

        ordered_elapsed = sorted(result.elapsed_ms for result in results)
        p95_index = min(
            len(ordered_elapsed) - 1,
            max(0, round((len(ordered_elapsed) - 1) * 0.95)),
        )
        rolling = any(case.current_weeks for case in suite)
        return {
            "suite": (
                "RetailAnalystBench-Rolling-v1"
                if rolling
                else "RetailAnalystBench-v1"
            ),
            "windows": (
                len({case.current_weeks for case in suite})
                if rolling
                else 1
            ),
            "gold_method": "independent_readonly_sql",
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
            "replan_rate": fmean(result.replanned for result in results),
            "mean_time_to_first_insight_ms": fmean(
                result.time_to_first_insight_ms for result in results
            ),
            "mean_elapsed_ms": fmean(result.elapsed_ms for result in results),
            "p95_elapsed_ms": ordered_elapsed[p95_index],
            "results": [result.__dict__ for result in results],
        }
