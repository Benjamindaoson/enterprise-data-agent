"""Result Validator - Validates SQL execution results.

This module validates:
- Column count and names
- Data types
- Time grain consistency
- Empty result handling
- Null value detection
- Duplicate detection
- Value range validation
- Expected row count
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    SQLValidationResult,
    ExecutionResult,
    ExecutionStatus,
    ResultValidationResult,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "result_validator")


@dataclass
class ColumnValidation:
    """Validation result for a single column."""

    column_name: str
    is_valid: bool
    expected_type: str | None
    actual_type: str | None
    null_count: int
    unique_count: int
    min_value: Any | None
    max_value: Any | None
    issues: list[str]


@dataclass
class ResultValidationConfig:
    """Configuration for result validation."""

    allow_empty: bool = False
    allow_nulls: bool = True
    check_duplicates: bool = True
    max_null_ratio: float = 0.5  # Allow up to 50% nulls
    expected_columns: list[str] | None = None
    expected_row_count_min: int | None = None
    expected_row_count_max: int | None = None


class ResultValidator:
    """Validates SQL execution results.

    This validator ensures:
    1. Column structure matches expectations
    2. Data types are correct
    3. Time grains are consistent
    4. Results are not empty when they shouldn't be
    5. Null values are within acceptable ranges
    6. No unexpected duplicates
    """

    def __init__(
        self,
        config: ResultValidationConfig | None = None,
    ) -> None:
        """Initialize result validator.

        Args:
            config: Validation configuration
        """
        self._config = config or ResultValidationConfig()

    def validate(
        self,
        result: ExecutionResult,
        expected_columns: list[str] | None = None,
        expected_types: dict[str, str] | None = None,
        time_grain: str | None = None,
    ) -> ResultValidationResult:
        """Validate execution result.

        Args:
            result: Execution result to validate
            expected_columns: Expected column names
            expected_types: Expected column types
            time_grain: Expected time grain

        Returns:
            Validation result
        """
        with trace_span("nl2sql.validate_result", {
            "row_count": result.row_count,
            "column_count": len(result.columns),
        }):
            if not result.success:
                return ResultValidationResult(
                    status=ExecutionStatus.EXECUTION_ERROR,
                    details=f"Execution failed: {result.error}",
                )

            column_validations: list[ColumnValidation] = []
            errors: list[str] = []
            warnings: list[str] = []

            # Check for empty result
            if result.row_count == 0:
                if not self._config.allow_empty:
                    errors.append("Result is empty but empty results not allowed")
                    return ResultValidationResult(
                        status=ExecutionStatus.EXECUTION_ERROR,
                        details="; ".join(errors),
                        is_empty=True,
                    )
                else:
                    warnings.append("Result is empty")

            # Validate column count
            if expected_columns:
                if len(result.columns) != len(expected_columns):
                    errors.append(
                        f"Column count mismatch: expected {len(expected_columns)}, "
                        f"got {len(result.columns)}"
                    )

            # Validate column names
            if expected_columns:
                for i, (expected, actual) in enumerate(
                    zip(expected_columns, result.columns)
                ):
                    if expected.lower() != actual.lower():
                        warnings.append(
                            f"Column name mismatch at index {i}: expected '{expected}', "
                            f"got '{actual}'"
                        )

            # Validate each column
            for i, col_name in enumerate(result.columns):
                # Extract column values - handle both dict and tuple rows
                col_values = []
                for row in result.rows:
                    if isinstance(row, dict):
                        col_values.append(row.get(col_name))
                    else:
                        col_values.append(row[i] if i < len(row) else None)

                col_validation = self._validate_column(
                    col_name,
                    col_values,
                    expected_types.get(col_name) if expected_types else None,
                    time_grain,
                )
                column_validations.append(col_validation)

                # Check for column-level errors
                if not col_validation.is_valid:
                    for issue in col_validation.issues:
                        errors.append(f"Column '{col_name}': {issue}")

                # Check for warnings
                if col_validation.null_count > 0:
                    null_ratio = col_validation.null_count / max(result.row_count, 1)
                    if null_ratio > self._config.max_null_ratio:
                        warnings.append(
                            f"Column '{col_name}' has {null_ratio:.1%} null values"
                        )

            # Check for duplicates
            if self._config.check_duplicates and result.rows:
                dup_result = self._check_duplicates(result.rows)
                if dup_result:
                    warnings.append(f"Duplicate rows detected: {dup_result}")

            # Check row count
            if self._config.expected_row_count_min is not None:
                if result.row_count < self._config.expected_row_count_min:
                    warnings.append(
                        f"Row count ({result.row_count}) below minimum "
                        f"({self._config.expected_row_count_min})"
                    )

            if self._config.expected_row_count_max is not None:
                if result.row_count > self._config.expected_row_count_max:
                    warnings.append(
                        f"Row count ({result.row_count}) above maximum "
                        f"({self._config.expected_row_count_max})"
                    )

            # Time grain validation
            if time_grain:
                grain_warning = self._validate_time_grain(result.rows, result.columns, time_grain)
                if grain_warning:
                    warnings.append(grain_warning)

            is_valid = len(errors) == 0

            logger.info(
                f"Result validation: {'PASSED' if is_valid else 'FAILED'}",
                extra={
                    "row_count": result.row_count,
                    "column_count": len(result.columns),
                    "errors": errors,
                    "warnings": warnings,
                }
            )

            return ResultValidationResult(
                status=ExecutionStatus.VALID if is_valid else ExecutionStatus.REJECTED,
                expected_columns=expected_columns or [],
                actual_columns=result.columns,
                column_match=len(expected_columns) == len(result.columns) if expected_columns else True,
                row_count=result.row_count,
                is_empty=result.row_count == 0,
                warnings=warnings,
                details="; ".join(errors) if errors else "",
            )

    def _validate_column(
        self,
        column_name: str,
        values: list[Any],
        expected_type: str | None,
        time_grain: str | None,
    ) -> ColumnValidation:
        """Validate a single column.

        Args:
            column_name: Column name
            values: Column values
            expected_type: Expected type
            time_grain: Time grain for time columns

        Returns:
            Column validation result
        """
        issues: list[str] = []
        actual_type = "unknown"
        null_count = 0
        unique_values: set[Any] = set()

        for value in values:
            if value is None:
                null_count += 1
                continue

            unique_values.add(value)

            # Infer type from first non-null value
            if actual_type == "unknown":
                if isinstance(value, bool):
                    actual_type = "boolean"
                elif isinstance(value, int):
                    actual_type = "integer"
                elif isinstance(value, float):
                    actual_type = "float"
                elif isinstance(value, str):
                    # Check if it's a date/time string
                    if self._looks_like_date(value):
                        actual_type = "date"
                    else:
                        actual_type = "string"
                elif isinstance(value, (date, datetime)):
                    actual_type = "date"
                else:
                    actual_type = str(type(value).__name__)

        # Validate type if expected
        if expected_type:
            if expected_type.lower() not in actual_type.lower():
                issues.append(
                    f"Type mismatch: expected {expected_type}, got {actual_type}"
                )

        # Check for all nulls
        if null_count == len(values) and values:
            issues.append("Column contains only null values")

        # Check for single value (no variance)
        if len(unique_values) == 1 and len(values) > 1:
            issues.append("Column has no variance (all same value)")

        is_valid = len(issues) == 0

        return ColumnValidation(
            column_name=column_name,
            is_valid=is_valid,
            expected_type=expected_type,
            actual_type=actual_type,
            null_count=null_count,
            unique_count=len(unique_values),
            min_value=min(v for v in values if v is not None) if unique_values else None,
            max_value=max(v for v in values if v is not None) if unique_values else None,
            issues=issues,
        )

    def _looks_like_date(self, value: str) -> bool:
        """Check if string looks like a date.

        Args:
            value: String value

        Returns:
            True if looks like date
        """
        import re

        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
            r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",  # ISO datetime
            r"^\d{2}/\d{2}/\d{4}$",  # MM/DD/YYYY
            r"^\d{2}-\d{2}-\d{4}$",  # DD-MM-YYYY
        ]

        for pattern in date_patterns:
            if re.match(pattern, value):
                return True

        return False

    def _check_duplicates(self, rows: list[tuple[Any, ...]]) -> str | None:
        """Check for duplicate rows.

        Args:
            rows: Result rows

        Returns:
            Description of duplicates or None
        """
        if not rows:
            return None

        seen: set[tuple[Any, ...]] = set()
        duplicates: list[tuple[Any, ...]] = []

        for row in rows:
            # Convert dict to tuple of sorted items for hashing, or use row directly if tuple
            if isinstance(row, dict):
                row_tuple = tuple(sorted(row.items()))
            else:
                row_tuple = tuple(row)

            if row_tuple in seen:
                duplicates.append(row_tuple)
            else:
                seen.add(row_tuple)

        if duplicates:
            # Count occurrences
            from collections import Counter

            def to_hashable(r):
                return tuple(sorted(r.items())) if isinstance(r, dict) else tuple(r)

            row_counts = Counter(to_hashable(r) for r in rows)
            dup_info = [
                f"({count}x: {row})" if not isinstance(row, dict) else f"({count}x: dict)"
                for row, count in row_counts.items()
                if count > 1
            ]
            return f"{len(duplicates)} duplicate rows: {', '.join(dup_info[:3])}"

        return None

    def _validate_time_grain(
        self,
        rows: list[tuple[Any, ...]],
        columns: list[str],
        time_grain: str,
    ) -> str | None:
        """Validate time grain consistency.

        Args:
            rows: Result rows
            columns: Column names
            time_grain: Expected time grain

        Returns:
            Warning message or None
        """
        # Find date column
        date_col_idx = None
        for i, col in enumerate(columns):
            col_lower = col.lower()
            if any(t in col_lower for t in ["date", "time", "day", "month", "year"]):
                date_col_idx = i
                break

        if date_col_idx is None:
            return None

        # Extract date values
        dates: list[date | datetime] = []
        date_col_name = columns[date_col_idx] if date_col_idx < len(columns) else None

        for row in rows:
            # Handle both dict and tuple rows
            if isinstance(row, dict) and date_col_name:
                value = row.get(date_col_name)
            else:
                value = row[date_col_idx] if date_col_idx < len(row) else None

            if isinstance(value, (date, datetime)):
                dates.append(value)
            elif isinstance(value, str) and self._looks_like_date(value):
                try:
                    dates.append(date.fromisoformat(value[:10]))
                except ValueError:
                    pass

        if len(dates) < 2:
            return None

        # Check grain consistency
        grain_lower = time_grain.lower()

        if "day" in grain_lower or "daily" in grain_lower:
            # Check if all dates are unique (daily grain)
            unique_days = set(d.date() if isinstance(d, datetime) else d for d in dates)
            if len(unique_days) < len(dates) * 0.9:
                return f"Time grain mismatch: expected daily but found duplicate dates"
            # Check intervals (should be ~1 day apart)
            for i in range(1, min(len(dates), 10)):
                diff = (dates[i] - dates[i-1]).days
                if diff > 7:
                    return f"Time grain mismatch: expected daily but found gaps of {diff} days"

        elif "month" in grain_lower or "monthly" in grain_lower:
            # Check if dates are at month boundaries
            months = set(
                (d.year, d.month) if isinstance(d, (date, datetime)) else None
                for d in dates
            )
            if None in months:
                months.discard(None)
            if len(months) < len(dates) * 0.5:
                return f"Time grain mismatch: expected monthly but found multiple values per month"

        elif "week" in grain_lower or "weekly" in grain_lower:
            # Check week consistency
            weeks = set(
                d.isocalendar()[1] if isinstance(d, (date, datetime)) else None
                for d in dates
            )
            if None in weeks:
                weeks.discard(None)
            if len(weeks) < len(dates) * 0.5:
                return f"Time grain mismatch: expected weekly but found multiple values per week"

        elif "year" in grain_lower or "yearly" in grain_lower or "annual" in grain_lower:
            # Check year consistency
            years = set(
                d.year if isinstance(d, (date, datetime)) else None
                for d in dates
            )
            if None in years:
                years.discard(None)
            if len(years) < len(dates) * 0.5:
                return f"Time grain mismatch: expected yearly but found multiple values per year"

        return None

    def validate_schema_match(
        self,
        result: ExecutionResult,
        expected_schema: dict[str, str],
    ) -> tuple[bool, list[str]]:
        """Validate that result schema matches expected schema.

        Args:
            result: Execution result
            expected_schema: Expected column -> type mapping

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors: list[str] = []

        # Check column count
        if len(result.columns) != len(expected_schema):
            errors.append(
                f"Column count mismatch: expected {len(expected_schema)}, "
                f"got {len(result.columns)}"
            )

        # Check column names and types
        for col_name, expected_type in expected_schema.items():
            if col_name not in result.columns:
                errors.append(f"Missing expected column: {col_name}")
                continue

            col_idx = result.columns.index(col_name)
            # Handle both dict and tuple/list rows
            values = []
            for row in result.rows:
                if isinstance(row, dict):
                    values.append(row.get(col_name))
                else:
                    values.append(row[col_idx] if col_idx < len(row) else None)

            # Infer actual type
            actual_type = "unknown"
            for value in values:
                if value is not None:
                    if isinstance(value, bool):
                        actual_type = "boolean"
                        break
                    elif isinstance(value, int):
                        actual_type = "integer"
                        break
                    elif isinstance(value, float):
                        actual_type = "float"
                        break
                    elif isinstance(value, str):
                        actual_type = "string"
                        break

            # Check type compatibility
            expected_lower = expected_type.lower()
            actual_lower = actual_type.lower()

            if expected_lower in ("number", "integer", "float") and actual_lower not in ("number", "integer", "float"):
                errors.append(f"Column {col_name}: type mismatch, expected {expected_type}, got {actual_type}")

            elif expected_lower == "string" and actual_lower not in ("string", "date"):
                errors.append(f"Column {col_name}: type mismatch, expected {expected_type}, got {actual_type}")

        return len(errors) == 0, errors
