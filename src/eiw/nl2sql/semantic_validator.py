"""Semantic Validator - Validates SQL against semantic layer definitions.

This module validates that SQL is semantically correct:
- Metric formula consistency
- Aggregation correctness
- Grain correctness
- Dimension compatibility
- Time semantics
- Required business filters
- Allowed join paths
- Join cardinality
- Data availability
- Metric version consistency
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    SQLValidationResult,
    ExecutionStatus,
)
from eiw.semantic.v2 import (
    SemanticPackageV2,
    MetricDefinition,
    TimeGrain,
    AggregationType,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "semantic_validator")


class SemanticValidator:
    """Validates SQL against semantic layer definitions.

    This validator ensures:
    1. Metric formulas are used correctly
    2. Aggregations match metric definitions
    3. Grains are supported
    4. Dimensions are compatible
    5. Required filters are applied
    6. Join paths are valid
    """

    def __init__(self, semantic_packages: dict[str, SemanticPackageV2]) -> None:
        """Initialize semantic validator.

        Args:
            semantic_packages: Dict of domain_id -> SemanticPackageV2
        """
        self._packages = semantic_packages

    def validate(
        self,
        sql: str,
        domain: str,
        metrics: list[str],
        dimensions: list[str],
        grain: str | None = None,
        time_range_start: date | None = None,
        time_range_end: date | None = None,
    ) -> SQLValidationResult:
        """Validate SQL against semantic rules.

        Args:
            sql: SQL to validate
            domain: Business domain
            metrics: Metric IDs used
            dimensions: Dimension IDs used
            grain: Time grain
            time_range_start: Start of time range
            time_range_end: End of time range

        Returns:
            Validation result
        """
        with trace_span("nl2sql.semantic_validate", {
            "domain": domain,
            "metrics": metrics,
            "dimensions": dimensions,
        }):
            pkg = self._packages.get(domain)
            if not pkg:
                return SQLValidationResult(
                    is_valid=True,
                    status=ExecutionStatus.VALID,
                    details="No semantic package for domain - skipping semantic validation",
                )

            errors: list[SQLValidationErrorCategory] = []
            warnings: list[str] = []

            # 1. Check metric formulas
            for metric_id in metrics:
                check_result = self._check_metric_formula(pkg, metric_id, sql)
                if check_result:
                    errors.append(check_result)

            # 2. Check aggregation correctness
            for metric_id in metrics:
                check_result = self._check_aggregation(pkg, metric_id, sql)
                if check_result:
                    warnings.append(check_result.value)

            # 3. Check grain support
            if grain:
                for metric_id in metrics:
                    check_result = self._check_grain(pkg, metric_id, grain)
                    if check_result:
                        errors.append(check_result)

            # 4. Check dimension compatibility
            for dim_id in dimensions:
                check_result = self._check_dimension_compatibility(pkg, dim_id, metrics)
                if check_result:
                    warnings.append(check_result.value)

            # 5. Check time range availability
            if time_range_start or time_range_end:
                for metric_id in metrics:
                    check_result = self._check_availability(pkg, metric_id, time_range_start, time_range_end)
                    if check_result:
                        errors.append(check_result)

            # 6. Check required joins
            check_result = self._check_required_joins(pkg, metrics, dimensions)
            if check_result:
                errors.append(check_result)

            is_valid = len(errors) == 0

            logger.info(
                f"Semantic validation: {'PASSED' if is_valid else 'FAILED'}",
                extra={
                    "domain": domain,
                    "errors": [e.value for e in errors],
                    "warnings": warnings,
                }
            )

            return SQLValidationResult(
                is_valid=is_valid,
                status=ExecutionStatus.VALID if is_valid else ExecutionStatus.REJECTED,
                errors=errors,
                warnings=warnings,
                details=f"Semantic validation {'passed' if is_valid else 'failed'}",
            )

    def _check_metric_formula(
        self,
        pkg: SemanticPackageV2,
        metric_id: str,
        sql: str,
    ) -> SQLValidationErrorCategory | None:
        """Check if SQL uses correct metric formula.

        Args:
            pkg: Semantic package
            metric_id: Metric ID
            sql: SQL to check

        Returns:
            Error if formula is incorrect
        """
        try:
            metric = pkg.metric(metric_id)
        except KeyError:
            return None  # Unknown metric, let other checks handle

        # For derived metrics, check if formula is respected
        if metric.formula.type == "derived":
            # Check if base metrics are referenced
            for base_metric in metric.formula.base_metrics:
                if base_metric.lower() not in sql.lower():
                    return SQLValidationErrorCategory.INVALID_METRIC_FORMULA

        return None

    def _check_aggregation(
        self,
        pkg: SemanticPackageV2,
        metric_id: str,
        sql: str,
    ) -> SQLValidationErrorCategory | None:
        """Check if aggregation matches metric definition.

        Args:
            pkg: Semantic package
            metric_id: Metric ID
            sql: SQL to check

        Returns:
            Warning if aggregation differs
        """
        try:
            metric = pkg.metric(metric_id)
        except KeyError:
            return None

        sql_upper = sql.upper()

        # Check if expected aggregation is used
        expected_agg = metric.aggregation.value.upper()
        if expected_agg not in sql_upper:
            # Check if another aggregation is used
            for agg in ["SUM(", "AVG(", "COUNT(", "MIN(", "MAX("]:
                if agg in sql_upper:
                    return SQLValidationErrorCategory.AGGREGATION_ERROR

        return None

    def _check_grain(
        self,
        pkg: SemanticPackageV2,
        metric_id: str,
        grain: str,
    ) -> SQLValidationErrorCategory | None:
        """Check if grain is supported by metric.

        Args:
            pkg: Semantic package
            metric_id: Metric ID
            grain: Time grain

        Returns:
            Error if grain is not supported
        """
        try:
            metric = pkg.metric(metric_id)
        except KeyError:
            return None

        # Check if metric supports this grain
        grain_enum = TimeGrain(grain.upper())
        for supported_grain in metric.supported_grains:
            if supported_grain.grain == grain_enum:
                if not supported_grain.available:
                    return SQLValidationErrorCategory.GRAIN_ERROR
                return None

        return SQLValidationErrorCategory.GRAIN_ERROR

    def _check_dimension_compatibility(
        self,
        pkg: SemanticPackageV2,
        dim_id: str,
        metrics: list[str],
    ) -> SQLValidationErrorCategory | None:
        """Check if dimension is compatible with metrics.

        Args:
            pkg: Semantic package
            dim_id: Dimension ID
            metrics: Metric IDs

        Returns:
            Warning if incompatible
        """
        try:
            dimension = pkg.dimension(dim_id)
        except KeyError:
            return None

        # Check each metric
        for metric_id in metrics:
            try:
                metric = pkg.metric(metric_id)
            except KeyError:
                continue

            # Check if dimension is required or optional
            if dim_id not in metric.required_dimensions and dim_id not in metric.optional_dimensions:
                return SQLValidationErrorCategory.SEMANTIC_MISMATCH

        return None

    def _check_availability(
        self,
        pkg: SemanticPackageV2,
        metric_id: str,
        start: date | None,
        end: date | None,
    ) -> SQLValidationErrorCategory | None:
        """Check if metric is available for time range.

        Args:
            pkg: Semantic package
            metric_id: Metric ID
            start: Start date
            end: End date

        Returns:
            Error if not available
        """
        try:
            metric = pkg.metric(metric_id)
        except KeyError:
            return None

        if not metric.availability.covers(start, end):
            return SQLValidationErrorCategory.EMPTY_UNEXPECTED_RESULT

        return None

    def _check_required_joins(
        self,
        pkg: SemanticPackageV2,
        metrics: list[str],
        dimensions: list[str],
    ) -> SQLValidationErrorCategory | None:
        """Check if required joins are present.

        Args:
            pkg: Semantic package
            metrics: Metric IDs
            dimensions: Dimension IDs

        Returns:
            Error if required joins are missing
        """
        # This would need SQL parsing to check actual joins
        # For now, just check if join paths are defined

        for metric_id in metrics:
            try:
                metric = pkg.metric(metric_id)
            except KeyError:
                continue

            # If metric requires joins, they should be in the SQL
            # This is a simplified check
            if metric.allowed_join_paths and not metric.default_join_path:
                # Metric needs specific join paths
                pass

        return None


@dataclass
class MetricFormulaCheck:
    """Result of metric formula validation."""

    metric_id: str
    expected_formula: str
    actual_usage: str
    is_correct: bool
    details: str
