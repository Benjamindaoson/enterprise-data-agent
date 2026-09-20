"""SQL Repair - Bounded SQL repair loop with error classification.

This module provides:
- Error classification
- Repair strategy selection
- Bounded repair loop
- Permission-aware repair
- Multiple repair attempts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    SQLValidationResult,
    ExecutionResult,
    ExecutionStatus,
    RepairAttempt,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "sql_repair")


class RepairStrategy(str, Enum):
    """Strategies for SQL repair."""

    NONE = "none"
    SIMPLIFY = "simplify"
    ADD_JOIN = "add_join"
    REMOVE_JOIN = "remove_join"
    ADD_FILTER = "add_filter"
    ADD_LIMIT = "add_limit"
    FIX_SYNTAX = "fix_syntax"
    ADD_GROUP_BY = "add_group_by"
    REMOVE_DIMENSION = "remove_dimension"
    CHANGE_AGGREGATION = "change_aggregation"
    USE_APPROXIMATE = "use_approximate"
    ESCALATE = "escalate"


class RepairClassification(str, Enum):
    """Classification of repair difficulty/risk."""

    SAFE = "safe"  # Low risk, common fixes
    MODERATE = "moderate"  # Medium risk, specific fixes
    RISKY = "risky"  # Higher risk, significant changes
    NEVER_REPAIR = "never"  # Should never be repaired (e.g., permission denied)


@dataclass
class RepairConfig:
    """Configuration for repair behavior."""

    max_repair_attempts: int = 3
    allow_permission_escalation: bool = False
    allow_simplification: bool = True
    allow_bypass: bool = False  # Allow bypassing checks
    complexity_threshold: float = 50.0


@dataclass
class RepairContext:
    """Context for repair decisions."""

    original_sql: str
    error_category: SQLValidationErrorCategory
    error_message: str
    domain: str | None = None
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    policy_context: Any = None  # PolicyContext from policy.py


class RepairStrategySelector:
    """Selects repair strategy based on error classification."""

    # Mapping from error category to classification and strategies
    ERROR_CLASSIFICATION: dict[SQLValidationErrorCategory, tuple[RepairClassification, list[RepairStrategy]]] = {
        SQLValidationErrorCategory.SYNTAX_ERROR: (
            RepairClassification.MODERATE,
            [RepairStrategy.FIX_SYNTAX, RepairStrategy.SIMPLIFY],
        ),
        SQLValidationErrorCategory.UNKNOWN_TABLE: (
            RepairClassification.RISKY,
            [RepairStrategy.SIMPLIFY, RepairStrategy.REMOVE_DIMENSION, RepairStrategy.ESCALATE],
        ),
        SQLValidationErrorCategory.UNKNOWN_COLUMN: (
            RepairClassification.RISKY,
            [RepairStrategy.SIMPLIFY, RepairStrategy.REMOVE_DIMENSION, RepairStrategy.ESCALATE],
        ),
        SQLValidationErrorCategory.INVALID_JOIN: (
            RepairClassification.MODERATE,
            [RepairStrategy.REMOVE_JOIN, RepairStrategy.SIMPLIFY],
        ),
        SQLValidationErrorCategory.AGGREGATION_ERROR: (
            RepairClassification.MODERATE,
            [RepairStrategy.CHANGE_AGGREGATION, RepairStrategy.SIMPLIFY],
        ),
        SQLValidationErrorCategory.GRAIN_ERROR: (
            RepairClassification.MODERATE,
            [RepairStrategy.SIMPLIFY, RepairStrategy.REMOVE_DIMENSION],
        ),
        SQLValidationErrorCategory.COMPLEXITY_EXCEEDED: (
            RepairClassification.SAFE,
            [RepairStrategy.ADD_LIMIT, RepairStrategy.SIMPLIFY],
        ),
        SQLValidationErrorCategory.PERMISSION_DENIED: (
            RepairClassification.NEVER_REPAIR,
            [RepairStrategy.ESCALATE],
        ),
        SQLValidationErrorCategory.SECURITY_POLICY: (
            RepairClassification.NEVER_REPAIR,
            [RepairStrategy.ESCALATE],
        ),
        SQLValidationErrorCategory.INVALID_METRIC_FORMULA: (
            RepairClassification.RISKY,
            [RepairStrategy.SIMPLIFY, RepairStrategy.USE_APPROXIMATE],
        ),
        SQLValidationErrorCategory.EMPTY_UNEXPECTED_RESULT: (
            RepairClassification.SAFE,
            [RepairStrategy.ADD_FILTER, RepairStrategy.SIMPLIFY],
        ),
        SQLValidationErrorCategory.SEMANTIC_MISMATCH: (
            RepairClassification.MODERATE,
            [RepairStrategy.REMOVE_DIMENSION, RepairStrategy.SIMPLIFY],
        ),
    }

    def classify(
        self,
        error: SQLValidationErrorCategory,
    ) -> tuple[RepairClassification, list[RepairStrategy]]:
        """Classify error and get repair strategies.

        Args:
            error: Error category

        Returns:
            Tuple of (classification, strategies)
        """
        return self.ERROR_CLASSIFICATION.get(
            error,
            (RepairClassification.MODERATE, [RepairStrategy.SIMPLIFY])
        )

    def should_repair(
        self,
        error: SQLValidationErrorCategory,
        config: RepairConfig,
        attempt_count: int,
    ) -> bool:
        """Determine if error should be repaired.

        Args:
            error: Error category
            config: Repair config
            attempt_count: Current attempt count

        Returns:
            True if should attempt repair
        """
        classification, _ = self.classify(error)

        # Never repair
        if classification == RepairClassification.NEVER_REPAIR:
            return False

        # Check max attempts
        if attempt_count >= config.max_repair_attempts:
            return False

        # Risky repairs require fewer attempts
        if classification == RepairClassification.RISKY and attempt_count >= 1:
            return False

        return True


class SQLRepair:
    """Performs bounded SQL repair with error classification.

    This repair module:
    1. Classifies errors by risk/feasibility
    2. Selects appropriate repair strategies
    3. Enforces bounded repair loop
    4. Never repairs permission_denied or security_policy errors
    5. Logs all repair attempts
    """

    def __init__(
        self,
        config: RepairConfig | None = None,
        generator: Any | None = None,  # SQLGeneratorProvider
    ) -> None:
        """Initialize SQL repair.

        Args:
            config: Repair configuration
            generator: SQL generator for generating repair SQL
        """
        self._config = config or RepairConfig()
        self._generator = generator
        self._selector = RepairStrategySelector()

    def repair(
        self,
        sql: str,
        errors: list[SQLValidationErrorCategory],
        execution_result: ExecutionResult | None = None,
        context: RepairContext | None = None,
    ) -> RepairAttempt | None:
        """Attempt to repair SQL based on errors.

        Args:
            sql: Original SQL
            errors: List of error categories
            execution_result: Execution result if available
            context: Repair context

        Returns:
            Repair attempt with repaired SQL or None
        """
        with trace_span("nl2sql.repair", {
            "attempt": 1,
            "errors": [e.value for e in errors],
        }):
            if not errors:
                return None

            # Classify errors
            repair_history: list[dict[str, Any]] = []
            current_sql = sql
            attempt_count = 0

            for error in errors:
                attempt_count += 1
                classification, strategies = self._selector.classify(error)

                # Never repair permission_denied or security errors
                if classification == RepairClassification.NEVER_REPAIR:
                    logger.warning(f"Error {error.value} classified as NEVER_REPAIR - skipping")
                    repair_history.append({
                        "error": error.value,
                        "classification": classification.value,
                        "skipped": True,
                        "reason": "Never repair this error type",
                    })
                    continue

                # Check if we should repair
                if not self._selector.should_repair(error, self._config, attempt_count):
                    repair_history.append({
                        "error": error.value,
                        "classification": classification.value,
                        "skipped": True,
                        "reason": "Max attempts exceeded or too risky",
                    })
                    continue

                # Try each strategy
                repaired = None
                for strategy in strategies:
                    if strategy == RepairStrategy.NONE:
                        continue

                    # Check if bypass is allowed
                    if strategy == RepairStrategy.ESCALATE:
                        repair_history.append({
                            "error": error.value,
                            "strategy": strategy.value,
                            "result": "escalated",
                        })
                        continue

                    # Attempt repair with this strategy
                    repaired = self._apply_strategy(
                        current_sql,
                        strategy,
                        error,
                        execution_result,
                        context,
                    )

                    if repaired:
                        repair_history.append({
                            "error": error.value,
                            "strategy": strategy.value,
                            "result": "success",
                            "repaired_sql": repaired,
                        })
                        current_sql = repaired
                        break
                    else:
                        repair_history.append({
                            "error": error.value,
                            "strategy": strategy.value,
                            "result": "failed",
                        })

                if not repaired:
                    repair_history.append({
                        "error": error.value,
                        "result": "no_strategy_worked",
                    })

            # Check if any repair was made
            if current_sql == sql:
                return None

            return RepairAttempt(
                attempt_number=attempt_count,
                original_sql=sql,
                error=", ".join(e.value for e in errors),
                error_category=errors[0] if errors else SQLValidationErrorCategory.SYNTAX_ERROR,
                repaired_sql=current_sql,
                explanation=f"Applied {len([h for h in repair_history if h.get('result') == 'success'])} repairs",
                success=True,
            )

    def _apply_strategy(
        self,
        sql: str,
        strategy: RepairStrategy,
        error: SQLValidationErrorCategory,
        execution_result: ExecutionResult | None,
        context: RepairContext | None,
    ) -> str | None:
        """Apply a repair strategy to SQL.

        Args:
            sql: SQL to repair
            strategy: Repair strategy
            error: Error being addressed
            execution_result: Execution result if available
            context: Repair context

        Returns:
            Repaired SQL or None
        """
        import re

        sql_upper = sql.upper()

        if strategy == RepairStrategy.ADD_LIMIT:
            # Add LIMIT clause if missing
            if "LIMIT" not in sql_upper:
                return f"{sql.rstrip().rstrip(';')} LIMIT 1000"

        elif strategy == RepairStrategy.SIMPLIFY:
            # Simplify query by removing complex clauses
            simplified = sql

            # Remove ORDER BY if present
            if " ORDER BY " in sql_upper:
                order_idx = sql_upper.rfind(" ORDER BY ")
                simplified = sql[:order_idx].rstrip().rstrip(';')

            # Ensure LIMIT is present
            if "LIMIT" not in simplified.upper():
                simplified = f"{simplified} LIMIT 100"

            return simplified

        elif strategy == RepairStrategy.REMOVE_JOIN:
            # Try to remove problematic joins
            # This is complex and would need SQL parsing
            return None  # Placeholder

        elif strategy == RepairStrategy.ADD_FILTER:
            # Add a filter to reduce result set
            if "WHERE" in sql_upper:
                # Add to existing WHERE
                if context and context.dimensions:
                    return f"{sql.rstrip().rstrip(';')} AND {context.dimensions[0]} IS NOT NULL"
            else:
                # Add new WHERE clause
                return f"{sql.rstrip().rstrip(';')} WHERE 1=1"

        elif strategy == RepairStrategy.REMOVE_DIMENSION:
            # Remove a dimension from GROUP BY
            if "GROUP BY" in sql_upper:
                # Would need SQL parsing to properly handle this
                return None

        elif strategy == RepairStrategy.CHANGE_AGGREGATION:
            # Change aggregation from COUNT to SUM or vice versa
            if "COUNT(" in sql_upper:
                return sql.upper().replace("COUNT(", "SUM(")
            elif "SUM(" in sql_upper:
                return sql.upper().replace("SUM(", "COUNT(")

        elif strategy == RepairStrategy.FIX_SYNTAX:
            # Basic syntax fixes
            fixed = sql

            # Ensure single space after commas
            fixed = re.sub(r',\s*', ', ', fixed)

            # Remove trailing semicolons if present
            fixed = fixed.rstrip().rstrip(';')

            # Ensure proper spacing around operators
            fixed = re.sub(r'\s*([=<>!]+)\s*', r' \1 ', fixed)

            return fixed

        elif strategy == RepairStrategy.USE_APPROXIMATE:
            # Use approximate/distinct counts instead of exact
            if "COUNT(*)" in sql_upper:
                return sql.upper().replace("COUNT(*)", "COUNT(DISTINCT id)")

        return None

    def get_repair_recommendation(
        self,
        errors: list[SQLValidationErrorCategory],
        context: RepairContext | None = None,
    ) -> dict[str, Any]:
        """Get repair recommendations without executing.

        Args:
            errors: List of error categories
            context: Repair context

        Returns:
            Recommendations dictionary
        """
        recommendations: list[dict[str, Any]] = []
        can_repair = True
        escalation_required = False

        for error in errors:
            classification, strategies = self._selector.classify(error)

            if classification == RepairClassification.NEVER_REPAIR:
                can_repair = False
                escalation_required = True

            recommendations.append({
                "error": error.value,
                "classification": classification.value,
                "strategies": [s.value for s in strategies],
                "can_repair": classification != RepairClassification.NEVER_REPAIR,
            })

        return {
            "can_repair": can_repair,
            "escalation_required": escalation_required,
            "recommendations": recommendations,
            "context": {
                "domain": context.domain if context else None,
                "metrics": context.metrics if context else [],
                "dimensions": context.dimensions if context else [],
            } if context else None,
        }


def create_repair(
    config: RepairConfig | None = None,
    generator: Any | None = None,
) -> SQLRepair:
    """Create a SQL repair instance.

    Args:
        config: Repair configuration
        generator: SQL generator

    Returns:
        SQLRepair instance
    """
    return SQLRepair(config=config, generator=generator)
