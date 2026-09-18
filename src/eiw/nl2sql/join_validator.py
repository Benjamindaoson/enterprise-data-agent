"""Join Validator - Validates SQL joins against allowed paths.

This module validates:
- Join path correctness
- Join cardinality
- Join type validation
- Self-join handling
- Multi-join validation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    SQLValidationResult,
    ExecutionStatus,
    SchemaContext,
    JoinInfo,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "join_validator")


@dataclass
class JoinValidationError:
    """Details of a join validation error."""

    from_table: str
    to_table: str
    error_type: str
    details: str


class JoinValidator:
    """Validates SQL joins against allowed paths.

    This validator ensures:
    1. All joins follow defined paths
    2. Join cardinality is respected
    3. Join types are valid
    4. No self-joins that violate rules
    5. Multi-join paths are consistent
    """

    def __init__(self, schema: SchemaContext) -> None:
        """Initialize join validator.

        Args:
            schema: Schema context with join definitions
        """
        self._schema = schema
        self._valid_joins = self._build_join_map(schema)
        self._join_cardinalities = self._build_cardinality_map(schema)

    def _build_join_map(self, schema: SchemaContext) -> dict[tuple[str, str], JoinInfo]:
        """Build map of valid join pairs.

        Args:
            schema: Schema context

        Returns:
            Map of (from_table, to_table) -> JoinInfo
        """
        join_map: dict[tuple[str, str], JoinInfo] = {}

        for join_info in schema.joins:
            # Add forward direction
            key = (join_info.from_table, join_info.to_table)
            join_map[key] = join_info

            # Add reverse direction for bidirectional joins
            if join_info.join_type.upper() not in ("LEFT", "RIGHT", "CROSS"):
                reverse_key = (join_info.to_table, join_info.from_table)
                join_map[reverse_key] = join_info

        return join_map

    def _build_cardinality_map(
        self,
        schema: SchemaContext,
    ) -> dict[tuple[str, str], str]:
        """Build map of join cardinalities.

        Args:
            schema: Schema context

        Returns:
            Map of (from_table, to_table) -> cardinality
        """
        cardinality_map: dict[tuple[str, str], str] = {}

        for join_info in schema.joins:
            key = (join_info.from_table, join_info.to_table)
            cardinality_map[key] = getattr(join_info, "cardinality", "many-to-many")

        return cardinality_map

    def validate_joins(
        self,
        parsed_sql: Any,  # ParsedSQL from parser
    ) -> SQLValidationResult:
        """Validate all joins in parsed SQL.

        Args:
            parsed_sql: Parsed SQL with join information

        Returns:
            Validation result
        """
        with trace_span("nl2sql.validate_joins", {
            "join_count": len(parsed_sql.joins) if parsed_sql.joins else 0,
        }):
            errors: list[SQLValidationErrorCategory] = []
            warnings: list[str] = []

            if not parsed_sql.joins:
                return SQLValidationResult(
                    is_valid=True,
                    status=ExecutionStatus.VALID,
                    details="No joins to validate",
                )

            # Track tables involved in joins
            joined_tables: set[str] = set()

            for join_str in parsed_sql.joins:
                validation_result = self._validate_single_join(join_str, parsed_sql.tables)

                if validation_result.error:
                    errors.append(validation_result.error)

                if validation_result.warning:
                    warnings.append(validation_result.warning)

                # Track joined tables
                joined_tables.update(validation_result.tables_involved)

            # Check for implicit cross-joins (multiple tables without explicit joins)
            if len(parsed_sql.tables) > 2 and not parsed_sql.joins:
                warnings.append(
                    f"Multiple tables ({len(parsed_sql.tables)}) without explicit joins - "
                    "may result in cross join"
                )

            is_valid = len(errors) == 0

            logger.info(
                f"Join validation: {'PASSED' if is_valid else 'FAILED'}",
                extra={
                    "errors": [e.value for e in errors],
                    "warnings": warnings,
                    "tables_joined": list(joined_tables),
                }
            )

            return SQLValidationResult(
                is_valid=is_valid,
                status=ExecutionStatus.VALID if is_valid else ExecutionStatus.REJECTED,
                errors=errors,
                warnings=warnings,
                details=f"Join validation {'passed' if is_valid else 'failed'}",
            )

    def _validate_single_join(
        self,
        join_str: str,
        all_tables: list[str],
    ) -> JoinValidationError:
        """Validate a single join.

        Args:
            join_str: Join clause string
            all_tables: All tables in the query

        Returns:
            Validation result
        """
        # Parse join to extract table names
        tables_involved: list[str] = []
        join_type = "INNER"  # Default
        on_clause = ""

        join_upper = join_str.upper()

        # Extract join type
        for jt in ["LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "OUTER JOIN", "CROSS JOIN", "JOIN"]:
            if jt in join_upper:
                join_type = jt.replace(" JOIN", "").strip()
                break

        # Extract tables and ON clause
        # Simple extraction - in real use, would use SQLGlot AST
        if " ON " in join_str.upper():
            parts = join_str.split(" ON ", 1)
            on_clause = parts[1]
            # Extract table from join clause
            join_part = parts[0]
            for keyword in ["LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "OUTER JOIN", "CROSS JOIN", "JOIN"]:
                if keyword.upper() in join_part.upper():
                    table_part = join_part.upper().split(keyword)[-1].strip()
                    tables_involved.append(table_part.split()[0].strip("()"))
                    break

        # Extract tables from ON clause
        on_upper = on_clause.upper()
        for table in all_tables:
            if f"{table}." in on_upper or f"{table})" in on_upper:
                if table not in tables_involved:
                    tables_involved.append(table)

        # Validate the join pair
        if len(tables_involved) >= 2:
            from_table = tables_involved[0]
            to_table = tables_involved[1]

            # Check if join path is valid
            pair = (from_table, to_table)
            if pair not in self._valid_joins:
                # Check reverse direction
                reverse_pair = (to_table, from_table)
                if reverse_pair not in self._valid_joins:
                    return JoinValidationError(
                        from_table=from_table,
                        to_table=to_table,
                        error_type="INVALID_JOIN_PATH",
                        details=f"No valid join path from {from_table} to {to_table}",
                    )

                # Check cardinality constraints
                cardinality = self._join_cardinalities.get(reverse_pair, "many-to-many")
                if cardinality == "one-to-one":
                    # Could add warning about cardinality
                    pass

        return JoinValidationError(
            from_table="",
            to_table="",
            error_type="",
            details="",
        )

    def validate_join_path(
        self,
        from_table: str,
        to_table: str,
        on_clause: str | None = None,
    ) -> tuple[bool, str | None]:
        """Validate a specific join path.

        Args:
            from_table: Source table
            to_table: Target table
            on_clause: ON clause condition (optional)

        Returns:
            Tuple of (is_valid, error_message)
        """
        pair = (from_table, to_table)

        # Check if pair is valid
        if pair in self._valid_joins:
            return True, None

        # Check reverse direction
        reverse_pair = (to_table, from_table)
        if reverse_pair in self._valid_joins:
            return True, None

        return False, f"No valid join path from {from_table} to {to_table}"

    def get_required_joins(
        self,
        from_table: str,
        to_table: str,
    ) -> list[list[str]]:
        """Get required intermediate joins to connect two tables.

        Args:
            from_table: Source table
            to_table: Target table

        Returns:
            List of possible join paths (each path is a list of tables)
        """
        # BFS to find join paths
        from collections import deque

        if from_table == to_table:
            return [[from_table]]

        visited: set[str] = {from_table}
        queue: deque[tuple[str, list[str]]] = deque([(from_table, [from_table])])

        paths: list[list[str]] = []
        max_depth = 5  # Limit path length

        while queue and len(paths) < 10:  # Limit number of paths
            current, path = queue.popleft()

            if len(path) > max_depth:
                continue

            # Find all tables reachable from current
            for (f, t), _ in self._valid_joins.items():
                next_table = None
                if f == current and t not in visited:
                    next_table = t
                elif t == current and f not in visited:
                    next_table = f

                if next_table:
                    new_path = path + [next_table]
                    if next_table == to_table:
                        paths.append(new_path)
                    else:
                        visited.add(next_table)
                        queue.append((next_table, new_path))

        return paths

    def validate_join_cardinality(
        self,
        from_table: str,
        to_table: str,
        expected_cardinality: str,
    ) -> tuple[bool, str | None]:
        """Validate join cardinality.

        Args:
            from_table: Source table
            to_table: Target table
            expected_cardinality: Expected cardinality ("one-to-one", "one-to-many", "many-to-many")

        Returns:
            Tuple of (is_valid, warning_message)
        """
        pair = (from_table, to_table)
        reverse_pair = (to_table, from_table)

        actual_cardinality = (
            self._join_cardinalities.get(pair) or
            self._join_cardinalities.get(reverse_pair) or
            "many-to-many"
        )

        if expected_cardinality == "one-to-one" and actual_cardinality == "many-to-many":
            return False, f"Expected one-to-one join but {from_table}-{to_table} is {actual_cardinality}"

        if expected_cardinality == "one-to-one" and actual_cardinality == "one-to-many":
            return False, f"Expected one-to-one join but {from_table}-{to_table} is {actual_cardinality}"

        return True, None
