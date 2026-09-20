"""Logical Query Planner - Creates structured query plans.

This module creates a LogicalQueryPlan before SQL generation:
- Purpose
- Metrics
- Dimensions
- Filters
- Time range
- Aggregation
- Grouping
- Ordering
- Joins
- Grain
- Limit
- Expected result shape
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from eiw.nl2sql.contracts import LogicalQueryPlan, SchemaContext
from eiw.semantic.v2 import SemanticPackageV2, MetricDefinition
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "query_planner")


class QueryPlanner:
    """Creates logical query plans from business questions.

    This planner:
    1. Analyzes the question
    2. Identifies metrics, dimensions, filters
    3. Determines aggregation, grouping, ordering
    4. Creates a structured plan for SQL generation
    """

    def __init__(self, semantic_packages: dict[str, SemanticPackageV2]) -> None:
        """Initialize query planner.

        Args:
            semantic_packages: Dict of domain_id -> SemanticPackageV2
        """
        self._packages = semantic_packages

    def plan(
        self,
        question: str,
        domain: str,
        schema: SchemaContext,
        resolved_metrics: list[str],
        resolved_dimensions: list[str],
        time_range_start: date | None = None,
        time_range_end: date | None = None,
    ) -> LogicalQueryPlan:
        """Create a logical query plan.

        Args:
            question: Natural language question
            domain: Business domain
            schema: Schema context
            resolved_metrics: Resolved metric IDs
            resolved_dimensions: Resolved dimension IDs
            time_range_start: Start of time range
            time_range_end: End of time range

        Returns:
            Logical query plan
        """
        with trace_span("nl2sql.plan", {
            "domain": domain,
            "metrics_count": len(resolved_metrics),
            "dimensions_count": len(resolved_dimensions),
        }):
            pkg = self._packages.get(domain)
            if not pkg:
                logger.warning(f"No semantic package for domain: {domain}")
                return self._create_empty_plan(question)

            plan = LogicalQueryPlan(
                purpose=self._determine_purpose(question),
                metrics=resolved_metrics,
                dimensions=resolved_dimensions,
                filters=self._extract_filters(question),
                time_range_start=time_range_start,
                time_range_end=time_range_end,
                grain=self._determine_grain(question),
                grouping=self._determine_grouping(resolved_dimensions, pkg),
                ordering=self._determine_ordering(question),
                joins=self._determine_joins(schema),
                limit=self._determine_limit(question),
            )

            # Determine aggregation based on metrics
            plan.aggregation = self._determine_aggregation(resolved_metrics, pkg)

            # Determine expected result shape
            plan.expected_result_shape = self._determine_result_shape(plan)

            # Determine source candidates
            plan.source_candidates = list(schema.tables.keys())

            logger.info(
                f"Query plan created: {len(plan.metrics)} metrics, {len(plan.dimensions)} dimensions",
                extra={
                    "purpose": plan.purpose,
                    "aggregation": plan.aggregation,
                    "grain": plan.grain,
                    "limit": plan.limit,
                }
            )

            return plan

    def _create_empty_plan(self, question: str) -> LogicalQueryPlan:
        """Create an empty plan for error cases.

        Args:
            question: Original question

        Returns:
            Empty logical plan
        """
        return LogicalQueryPlan(
            purpose="unknown",
            question=question,
        )

    def _determine_purpose(self, question: str) -> str:
        """Determine the purpose of the query.

        Args:
            question: Natural language question

        Returns:
            Purpose string
        """
        question_lower = question.lower()

        if any(word in question_lower for word in ["total", "sum", "aggregate"]):
            return "aggregation"
        elif any(word in question_lower for word in ["trend", "over time", "history", "change"]):
            return "trend_analysis"
        elif any(word in question_lower for word in ["top", "bottom", "rank", "largest", "smallest"]):
            return "ranking"
        elif any(word in question_lower for word in ["compare", "versus", "vs", "difference"]):
            return "comparison"
        elif any(word in question_lower for word in ["average", "mean", "typical"]):
            return "averaging"
        elif any(word in question_lower for word in ["count", "number of", "how many"]):
            return "counting"
        elif any(word in question_lower for word in ["percentage", "%", "rate", "ratio"]):
            return "ratio_calculation"
        elif any(word in question_lower for word in ["breakdown", "by", "grouped", "segment"]):
            return "breakdown"
        else:
            return "general_query"

    def _extract_filters(self, question: str) -> dict[str, Any]:
        """Extract filters from the question.

        Args:
            question: Natural language question

        Returns:
            Dictionary of filters
        """
        filters: dict[str, Any] = {}
        question_lower = question.lower()

        # Time-based filters
        if "last month" in question_lower:
            filters["time_period"] = "last_month"
        elif "last quarter" in question_lower:
            filters["time_period"] = "last_quarter"
        elif "last year" in question_lower:
            filters["time_period"] = "last_year"
        elif "ytd" in question_lower or "year to date" in question_lower:
            filters["time_period"] = "ytd"
        elif "mtd" in question_lower or "month to date" in question_lower:
            filters["time_period"] = "mtd"
        elif "qtd" in question_lower or "quarter to date" in question_lower:
            filters["time_period"] = "qtd"
        elif "yoy" in question_lower or "year over year" in question_lower:
            filters["time_period"] = "yoy"
        elif "mom" in question_lower or "month over month" in question_lower:
            filters["time_period"] = "mom"
        elif "qoq" in question_lower or "quarter over quarter" in question_lower:
            filters["time_period"] = "qoq"

        # Comparison filters
        if "greater than" in question_lower or "more than" in question_lower:
            match = _extract_number_after(question_lower, ["greater than", "more than"])
            if match:
                filters["value_min"] = match
        elif "less than" in question_lower:
            match = _extract_number_after(question_lower, ["less than"])
            if match:
                filters["value_max"] = match

        # Top/Bottom filters
        if "top" in question_lower:
            match = _extract_number_after(question_lower, ["top"])
            if match:
                filters["top_n"] = match
        elif "bottom" in question_lower:
            match = _extract_number_after(question_lower, ["bottom"])
            if match:
                filters["bottom_n"] = match

        # Trend filters
        if "increasing" in question_lower or "growing" in question_lower:
            filters["trend_direction"] = "increasing"
        elif "decreasing" in question_lower or "declining" in question_lower:
            filters["trend_direction"] = "decreasing"

        return filters

    def _determine_grain(self, question: str) -> str | None:
        """Determine time grain.

        Args:
            question: Natural language question

        Returns:
            Time grain or None
        """
        question_lower = question.lower()

        if "daily" in question_lower or "day" in question_lower:
            return "DAILY"
        elif "weekly" in question_lower or "week" in question_lower:
            return "WEEKLY"
        elif "monthly" in question_lower or "month" in question_lower:
            return "MONTHLY"
        elif "quarterly" in question_lower or "quarter" in question_lower:
            return "QUARTERLY"
        elif "yearly" in question_lower or "annual" in question_lower or "year" in question_lower:
            return "YEARLY"

        return None

    def _determine_grouping(
        self,
        dimensions: list[str],
        pkg: SemanticPackageV2,
    ) -> list[str]:
        """Determine grouping columns.

        Args:
            dimensions: Resolved dimension IDs
            pkg: Semantic package

        Returns:
            List of columns to group by
        """
        grouping = []

        for dim_id in dimensions:
            try:
                dim = pkg.dimension(dim_id)
                # Add dimension source column
                if dim.source_column:
                    grouping.append(dim.source_column)
            except KeyError:
                # Dimension not found, add as-is
                grouping.append(dim_id)

        return grouping

    def _determine_ordering(self, question: str) -> list[dict[str, str]]:
        """Determine ordering.

        Args:
            question: Natural language question

        Returns:
            List of ordering specifications
        """
        ordering: list[dict[str, str]] = []
        question_lower = question.lower()

        if "top" in question_lower:
            ordering.append({"column": "value", "direction": "DESC"})
        elif "bottom" in question_lower:
            ordering.append({"column": "value", "direction": "ASC"})
        elif "ascending" in question_lower or "lowest" in question_lower:
            ordering.append({"column": "value", "direction": "ASC"})
        elif "descending" in question_lower or "highest" in question_lower:
            ordering.append({"column": "value", "direction": "DESC"})
        elif "newest" in question_lower or "latest" in question_lower:
            ordering.append({"column": "date", "direction": "DESC"})
        elif "oldest" in question_lower:
            ordering.append({"column": "date", "direction": "ASC"})

        return ordering

    def _determine_joins(self, schema: SchemaContext) -> list[dict[str, str]]:
        """Determine required joins.

        Args:
            schema: Schema context

        Returns:
            List of join specifications
        """
        joins: list[dict[str, str]] = []

        for join_info in schema.joins:
            joins.append({
                "from_table": join_info.from_table,
                "from_column": join_info.from_column,
                "to_table": join_info.to_table,
                "to_column": join_info.to_column,
                "join_type": join_info.join_type,
            })

        return joins

    def _determine_limit(self, question: str) -> int | None:
        """Determine result limit.

        Args:
            question: Natural language question

        Returns:
            Row limit or None
        """
        question_lower = question.lower()

        # Extract number after "top" or "bottom"
        if "top" in question_lower:
            match = _extract_number_after(question_lower, ["top"])
            if match:
                return min(match, 100)  # Cap at 100
        elif "bottom" in question_lower:
            match = _extract_number_after(question_lower, ["bottom"])
            if match:
                return min(match, 100)

        # Default limits for certain query types
        if "list all" in question_lower:
            return 1000

        return None

    def _determine_aggregation(
        self,
        metrics: list[str],
        pkg: SemanticPackageV2,
    ) -> str | None:
        """Determine aggregation type.

        Args:
            metrics: Metric IDs
            pkg: Semantic package

        Returns:
            Aggregation type or None
        """
        for metric_id in metrics:
            try:
                metric = pkg.metric(metric_id)
                return metric.aggregation.value
            except KeyError:
                continue

        return None

    def _determine_result_shape(self, plan: LogicalQueryPlan) -> str:
        """Determine expected result shape.

        Args:
            plan: Logical query plan

        Returns:
            Result shape description
        """
        if plan.grouping and len(plan.grouping) > 0:
            if plan.limit and plan.limit <= 10:
                return "top_k_breakdown"
            elif plan.aggregation:
                return "aggregated_breakdown"
            else:
                return "detailed_breakdown"
        elif plan.aggregation:
            return "single_aggregate"
        elif plan.metrics:
            return "metric_value"
        else:
            return "raw_data"


def _extract_number_after(text: str, keywords: list[str]) -> int | None:
    """Extract a number that appears after any of the keywords.

    Args:
        text: Text to search
        keywords: Keywords to look for

    Returns:
        Extracted number or None
    """
    import re

    for keyword in keywords:
        idx = text.find(keyword)
        if idx >= 0:
            # Look for a number after the keyword
            after = text[idx + len(keyword):]
            match = re.search(r"(\d+)", after)
            if match:
                return int(match.group(1))

    return None
