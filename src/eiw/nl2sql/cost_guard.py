"""Cost Guard - EXPLAIN analysis and query cost estimation.

This module provides:
- SQL EXPLAIN analysis
- Row estimate extraction
- Complexity signal detection
- Query timeout enforcement
- Cost threshold validation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    SQLValidationResult,
    ExecutionStatus,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "cost_guard")


@dataclass
class CostEstimate:
    """Cost estimate from EXPLAIN."""

    estimated_rows: int | None
    estimated_cost: float | None
    estimated_time_ms: float | None
    plan_nodes: int
    contains_seq_scan: bool
    contains_nested_loop: bool
    contains_hash_join: bool
    contains_index_scan: bool
    complexity_score: float


@dataclass
class CostThreshold:
    """Cost threshold configuration."""

    max_rows: int = 1000000
    max_cost: float = 100000.0
    max_time_ms: float = 30000.0  # 30 seconds
    max_plan_nodes: int = 50
    max_complexity_score: float = 100.0


class CostGuard:
    """Guards against expensive queries using EXPLAIN analysis.

    This guard:
    1. Runs EXPLAIN on SQL
    2. Extracts row estimates
    3. Detects complexity signals
    4. Validates against thresholds
    5. Enforces timeout
    """

    def __init__(
        self,
        executor: Any,  # ExecutorProvider
        thresholds: CostThreshold | None = None,
    ) -> None:
        """Initialize cost guard.

        Args:
            executor: Executor provider for running EXPLAIN
            thresholds: Cost thresholds (uses defaults if None)
        """
        self._executor = executor
        self._thresholds = thresholds or CostThreshold()

    def analyze(
        self,
        sql: str,
        dialect: str = "postgres",
    ) -> CostEstimate:
        """Analyze SQL query cost using EXPLAIN.

        Args:
            sql: SQL to analyze
            dialect: SQL dialect for EXPLAIN format

        Returns:
            Cost estimate
        """
        with trace_span("nl2sql.cost_analyze", {
            "dialect": dialect,
            "sql_length": len(sql),
        }):
            explain_sql = self._build_explain_sql(sql, dialect)

            try:
                # Run EXPLAIN
                result = self._executor.execute_sync(
                    explain_sql,
                    timeout_ms=5000,  # 5 second timeout for EXPLAIN
                )

                # Parse EXPLAIN output
                estimate = self._parse_explain_output(result, dialect)

                logger.info(
                    f"Cost analysis: {estimate.estimated_rows} rows, cost={estimate.estimated_cost}",
                    extra={
                        "estimated_rows": estimate.estimated_rows,
                        "estimated_cost": estimate.estimated_cost,
                        "complexity_score": estimate.complexity_score,
                    }
                )

                return estimate

            except Exception as e:
                logger.warning(f"EXPLAIN analysis failed: {e}")
                # Return conservative estimate on failure
                return CostEstimate(
                    estimated_rows=None,
                    estimated_cost=None,
                    estimated_time_ms=None,
                    plan_nodes=0,
                    contains_seq_scan=False,
                    contains_nested_loop=False,
                    contains_hash_join=False,
                    contains_index_scan=False,
                    complexity_score=50.0,  # Conservative middle ground
                )

    def validate(
        self,
        sql: str,
        dialect: str = "postgres",
    ) -> SQLValidationResult:
        """Validate query cost against thresholds.

        Args:
            sql: SQL to validate
            dialect: SQL dialect

        Returns:
            Validation result
        """
        with trace_span("nl2sql.cost_validate", {
            "dialect": dialect,
        }):
            estimate = self.analyze(sql, dialect)
            errors: list[SQLValidationErrorCategory] = []
            warnings: list[str] = []

            # Check row estimate
            if estimate.estimated_rows is not None:
                if estimate.estimated_rows > self._thresholds.max_rows:
                    errors.append(SQLValidationErrorCategory.COMPLEXITY_EXCEEDED)
                    warnings.append(
                        f"Estimated rows ({estimate.estimated_rows}) exceeds threshold "
                        f"({self._thresholds.max_rows})"
                    )

            # Check cost
            if estimate.estimated_cost is not None:
                if estimate.estimated_cost > self._thresholds.max_cost:
                    errors.append(SQLValidationErrorCategory.COMPLEXITY_EXCEEDED)
                    warnings.append(
                        f"Estimated cost ({estimate.estimated_cost:.2f}) exceeds threshold "
                        f"({self._thresholds.max_cost:.2f})"
                    )

            # Check time
            if estimate.estimated_time_ms is not None:
                if estimate.estimated_time_ms > self._thresholds.max_time_ms:
                    warnings.append(
                        f"Estimated time ({estimate.estimated_time_ms:.0f}ms) exceeds "
                        f"threshold ({self._thresholds.max_time_ms:.0f}ms)"
                    )

            # Check plan nodes
            if estimate.plan_nodes > self._thresholds.max_plan_nodes:
                warnings.append(
                    f"Plan complexity ({estimate.plan_nodes} nodes) is high"
                )

            # Check complexity score
            if estimate.complexity_score > self._thresholds.max_complexity_score:
                errors.append(SQLValidationErrorCategory.COMPLEXITY_EXCEEDED)

            # Add warnings for complexity signals
            if estimate.contains_seq_scan and estimate.estimated_rows and estimate.estimated_rows > 10000:
                warnings.append("Query contains sequential scan on large table")

            if estimate.contains_nested_loop:
                warnings.append("Query uses nested loop join - may be slow for large datasets")

            is_valid = len(errors) == 0

            return SQLValidationResult(
                is_valid=is_valid,
                status=ExecutionStatus.VALID if is_valid else ExecutionStatus.REJECTED,
                errors=errors,
                warnings=warnings,
                details=f"Cost validation {'passed' if is_valid else 'failed'}",
            )

    def _build_explain_sql(self, sql: str, dialect: str) -> str:
        """Build EXPLAIN SQL for the dialect.

        Args:
            sql: Original SQL
            dialect: SQL dialect

        Returns:
            EXPLAIN SQL
        """
        dialect_lower = dialect.lower()

        if dialect_lower == "postgres" or dialect_lower == "postgresql":
            # PostgreSQL EXPLAIN with costs
            return f"EXPLAIN (FORMAT JSON, COSTS true, ANALYZE false) {sql}"
        elif dialect_lower == "duckdb":
            # DuckDB uses EXPLAIN
            return f"EXPLAIN {sql}"
        elif dialect_lower == "mysql":
            # MySQL uses EXPLAIN
            return f"EXPLAIN {sql}"
        elif dialect_lower == "snowflake":
            # Snowflake uses EXPLAIN
            return f"EXPLAIN {sql}"
        else:
            # Default to standard EXPLAIN
            return f"EXPLAIN {sql}"

    def _parse_explain_output(
        self,
        result: Any,  # ExecutionResult
        dialect: str,
    ) -> CostEstimate:
        """Parse EXPLAIN output into CostEstimate.

        Args:
            result: Execution result from EXPLAIN
            dialect: SQL dialect

        Returns:
            Cost estimate
        """
        # Extract raw output
        if hasattr(result, "rows"):
            raw_output = str(result.rows)
        elif hasattr(result, "data"):
            raw_output = str(result.data)
        else:
            raw_output = str(result)

        dialect_lower = dialect.lower()
        estimated_rows: int | None = None
        estimated_cost: float | None = None
        estimated_time_ms: float | None = None
        plan_nodes = 0
        contains_seq_scan = False
        contains_nested_loop = False
        contains_hash_join = False
        contains_index_scan = False
        complexity_score = 0.0

        # Parse based on dialect
        raw_upper = raw_output.upper()

        if dialect_lower == "postgres":
            # Try to parse JSON EXPLAIN output
            try:
                import json
                # Extract JSON from output
                import re
                json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
                if json_match:
                    explain_data = json.loads(json_match.group())
                    plan = explain_data.get("plan", {})

                    # Extract costs
                    estimated_rows = int(plan.get("Plan Rows", 0))
                    total_cost = plan.get("Total Cost", 0)
                    if total_cost:
                        estimated_cost = float(total_cost)

                    # Extract time if available
                    if "Actual Total Time" in plan:
                        estimated_time_ms = float(plan.get("Actual Total Time", 0)) * 1000

                    # Count nodes and detect patterns
                    self._analyze_plan_nodes(plan, {
                        "contains_seq_scan": False,
                        "contains_nested_loop": False,
                        "contains_hash_join": False,
                        "contains_index_scan": False,
                        "node_count": 0,
                        "complexity_score": 0.0,
                    })

                    contains_seq_scan = "Seq Scan" in raw_output
                    contains_nested_loop = "Nested Loop" in raw_output
                    contains_hash_join = "Hash Join" in raw_output
                    contains_index_scan = "Index Scan" in raw_output

                    # Count plan nodes
                    plan_nodes = raw_output.count("->")

            except (json.JSONDecodeError, Exception):
                pass

        # Fallback: simple regex-based extraction
        if estimated_rows is None:
            import re
            # Try to find "rows=X" pattern
            rows_match = re.search(r'rows[:\s]*(\d+)', raw_output, re.IGNORECASE)
            if rows_match:
                estimated_rows = int(rows_match.group(1))

        if estimated_cost is None:
            import re
            # Try to find "cost=X" pattern
            cost_match = re.search(r'cost[:\s]*=?\s*([\d.]+)', raw_output, re.IGNORECASE)
            if cost_match:
                estimated_cost = float(cost_match.group(1))

        # Count complexity signals
        plan_nodes = raw_output.count("->")
        contains_seq_scan = "SEQ SCAN" in raw_upper or "SEQUENTIAL SCAN" in raw_upper
        contains_nested_loop = "NESTED LOOP" in raw_upper
        contains_hash_join = "HASH JOIN" in raw_upper or "HASH" in raw_upper
        contains_index_scan = "INDEX SCAN" in raw_upper

        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(
            estimated_rows or 0,
            estimated_cost or 0,
            plan_nodes,
            contains_seq_scan,
            contains_nested_loop,
            contains_hash_join,
        )

        return CostEstimate(
            estimated_rows=estimated_rows,
            estimated_cost=estimated_cost,
            estimated_time_ms=estimated_time_ms,
            plan_nodes=plan_nodes,
            contains_seq_scan=contains_seq_scan,
            contains_nested_loop=contains_nested_loop,
            contains_hash_join=contains_hash_join,
            contains_index_scan=contains_index_scan,
            complexity_score=complexity_score,
        )

    def _analyze_plan_nodes(
        self,
        plan: dict[str, Any],
        stats: dict[str, Any],
    ) -> None:
        """Recursively analyze plan nodes.

        Args:
            plan: Plan node
            stats: Stats dict to update
        """
        stats["node_count"] = stats.get("node_count", 0) + 1

        node_type = plan.get("Node Type", "").upper()
        if "SEQ SCAN" in node_type:
            stats["contains_seq_scan"] = True
        if "NESTED LOOP" in node_type:
            stats["contains_nested_loop"] = True
        if "HASH JOIN" in node_type or "HASH" in node_type:
            stats["contains_hash_join"] = True
        if "INDEX SCAN" in node_type:
            stats["contains_index_scan"] = True

        # Recurse into subplans
        if "Plans" in plan:
            for sub_plan in plan["Plans"]:
                self._analyze_plan_nodes(sub_plan, stats)

    def _calculate_complexity_score(
        self,
        estimated_rows: int,
        estimated_cost: float,
        plan_nodes: int,
        contains_seq_scan: bool,
        contains_nested_loop: bool,
        contains_hash_join: bool,
    ) -> float:
        """Calculate a complexity score for the query.

        Args:
            estimated_rows: Estimated rows
            estimated_cost: Estimated cost
            plan_nodes: Number of plan nodes
            contains_seq_scan: Whether contains sequential scan
            contains_nested_loop: Whether contains nested loop
            contains_hash_join: Whether contains hash join

        Returns:
            Complexity score (0-100)
        """
        score = 0.0

        # Row-based scoring
        if estimated_rows > 1000000:
            score += 40
        elif estimated_rows > 100000:
            score += 30
        elif estimated_rows > 10000:
            score += 20
        elif estimated_rows > 1000:
            score += 10

        # Cost-based scoring
        if estimated_cost > 100000:
            score += 30
        elif estimated_cost > 10000:
            score += 20
        elif estimated_cost > 1000:
            score += 10

        # Plan node scoring
        if plan_nodes > 30:
            score += 15
        elif plan_nodes > 10:
            score += 10
        elif plan_nodes > 5:
            score += 5

        # Operation-based scoring
        if contains_seq_scan:
            score += 10
        if contains_nested_loop:
            score += 5
        if contains_hash_join:
            score += 2

        return min(score, 100.0)

    def estimate_timeout(self, estimate: CostEstimate) -> int:
        """Estimate appropriate timeout for query based on cost.

        Args:
            estimate: Cost estimate

        Returns:
            Suggested timeout in milliseconds
        """
        # Base timeout
        timeout_ms = 10000  # 10 seconds

        # Adjust based on estimated rows
        if estimate.estimated_rows:
            if estimate.estimated_rows > 1000000:
                timeout_ms = 120000  # 2 minutes
            elif estimate.estimated_rows > 100000:
                timeout_ms = 60000  # 1 minute
            elif estimate.estimated_rows > 10000:
                timeout_ms = 30000  # 30 seconds

        # Adjust based on cost
        if estimate.estimated_cost:
            if estimate.estimated_cost > 100000:
                timeout_ms = max(timeout_ms, 180000)  # 3 minutes
            elif estimate.estimated_cost > 10000:
                timeout_ms = max(timeout_ms, 60000)  # 1 minute

        # Adjust based on time estimate
        if estimate.estimated_time_ms:
            timeout_ms = max(timeout_ms, int(estimate.estimated_time_ms * 2))

        return min(timeout_ms, 300000)  # Cap at 5 minutes
