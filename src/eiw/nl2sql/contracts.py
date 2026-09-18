"""NL2SQL Pipeline Contracts and Data Models.

This module defines the core contracts for the governed NL2SQL pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Validation Error Categories
# =============================================================================


class SQLValidationErrorCategory(str, Enum):
    """Categories of SQL validation errors."""

    SYNTAX_ERROR = "syntax_error"
    UNKNOWN_TABLE = "unknown_table"
    UNKNOWN_COLUMN = "unknown_column"
    INVALID_JOIN = "invalid_join"
    INVALID_ALIAS = "invalid_alias"
    AGGREGATION_ERROR = "aggregation_error"
    GRAIN_ERROR = "grain_error"
    SEMANTIC_MISMATCH = "semantic_mismatch"
    EMPTY_UNEXPECTED_RESULT = "empty_unexpected_result"
    RESULT_SHAPE_MISMATCH = "result_shape_mismatch"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    COMPLEXITY_EXCEEDED = "complexity_exceeded"
    SECURITY_POLICY = "security_policy"
    INVALID_COLUMN_REFERENCE = "invalid_column_reference"
    INVALID_METRIC_FORMULA = "invalid_metric_formula"


# =============================================================================
# Query Lane Types
# =============================================================================


class QueryLane(str, Enum):
    """Query execution lanes."""

    DETERMINISTIC = "deterministic"  # Known metrics via semantic layer
    GOVERNED_NL2SQL = "governed_nl2sql"  # LLM-generated SQL
    UNKNOWN = "unknown"


# =============================================================================
# Execution Status
# =============================================================================


class ExecutionStatus(str, Enum):
    """Execution result status."""

    VALID = "VALID"
    REPAIRABLE = "REPAIRABLE"
    REJECTED = "REJECTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"


# =============================================================================
# Schema Context
# =============================================================================


class TableInfo(BaseModel):
    """Information about a database table."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(description="Table name")
    schema: str = Field(default="public", description="Schema name", validation_alias="schema")
    description: str = Field(default="", description="Business description")
    columns: list[ColumnInfo] = Field(default_factory=list)
    primary_key: str | None = Field(default=None, description="Primary key column")
    row_count_estimate: int | None = Field(default=None, description="Estimated row count")
    is_sensitive: bool = Field(default=False, description="Contains sensitive data")
    classification: str = Field(default="INTERNAL", description="Data classification")


class ColumnInfo(BaseModel):
    """Information about a database column."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Column name")
    data_type: str = Field(description="SQL data type")
    description: str = Field(default="", description="Business description")
    is_nullable: bool = Field(default=True, description="Whether column allows NULL")
    is_primary_key: bool = Field(default=False, description="Is part of primary key")
    is_foreign_key: bool = Field(default=False, description="Is foreign key")
    referenced_table: str | None = Field(default=None, description="Referenced table")
    referenced_column: str | None = Field(default=None, description="Referenced column")
    sample_values: list[str] = Field(default_factory=list, description="Sample values")
    is_sensitive: bool = Field(default=False, description="Contains sensitive data")
    policy_tags: list[str] = Field(default_factory=list, description="Policy tags")


class JoinInfo(BaseModel):
    """Information about a valid join between tables."""

    model_config = ConfigDict(extra="forbid")

    from_table: str = Field(description="Source table")
    from_column: str = Field(description="Source column")
    to_table: str = Field(description="Target table")
    to_column: str = Field(description="Target column")
    join_type: str = Field(default="INNER", description="Join type")
    cardinality: str = Field(default="many_to_one", description="Join cardinality")


@dataclass
class SchemaContext:
    """Context about available schema for SQL generation."""

    tables: dict[str, TableInfo] = field(default_factory=dict)
    joins: list[JoinInfo] = field(default_factory=list)
    domain: str = ""

    def get_table(self, name: str) -> TableInfo | None:
        """Get table by name."""
        return self.tables.get(name)

    def get_join_candidates(self, table_name: str) -> list[JoinInfo]:
        """Get valid joins for a table."""
        return [
            j for j in self.joins
            if j.from_table == table_name or j.to_table == table_name
        ]


# =============================================================================
# Request/Response Models
# =============================================================================


class NL2SQLRequest(BaseModel):
    """Request for NL2SQL generation."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000, description="Natural language question")
    domain: str = Field(description="Business domain")
    user_roles: list[str] = Field(default_factory=list, description="User roles")
    user_id: str | None = Field(default=None, description="User identifier")
    tenant_id: str | None = Field(default=None, description="Tenant identifier")
    time_range_start: date | None = Field(default=None, description="Start of time range")
    time_range_end: date | None = Field(default=None, description="End of time range")

    # Constraints
    max_complexity: int = Field(default=10, ge=1, le=100, description="Max query complexity")
    max_rows: int = Field(default=10000, ge=1, le=1000000, description="Max result rows")
    execution_timeout_seconds: int = Field(default=30, ge=1, le=300, description="Query timeout")

    # Context from semantic layer
    resolved_metrics: list[str] = Field(default_factory=list, description="Resolved metric IDs")
    resolved_dimensions: list[str] = Field(default_factory=list, description="Resolved dimension IDs")
    business_context: dict[str, Any] = Field(default_factory=dict, description="Additional business context")


class LogicalQueryPlan(BaseModel):
    """Logical query plan before SQL generation."""

    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(description="Query purpose/objective")
    metrics: list[str] = Field(default_factory=list, description="Metrics to calculate")
    dimensions: list[str] = Field(default_factory=list, description="Dimensions to group by")
    filters: dict[str, Any] = Field(default_factory=dict, description="Filters to apply")
    time_range_start: date | None = None
    time_range_end: date | None = None
    aggregation: str | None = Field(default=None, description="Aggregation type")
    grouping: list[str] = Field(default_factory=list, description="Group by columns")
    ordering: list[dict[str, str]] = Field(default_factory=list, description="Order by columns")
    joins: list[dict[str, str]] = Field(default_factory=list, description="Required joins")
    grain: str | None = Field(default=None, description="Time grain")
    limit: int | None = Field(default=None, ge=1, description="Row limit")
    expected_result_shape: str | None = Field(default=None, description="Expected result shape")
    source_candidates: list[str] = Field(default_factory=list, description="Candidate source tables")


class GeneratedSQL(BaseModel):
    """Generated SQL with metadata."""

    model_config = ConfigDict(extra="forbid")

    sql: str = Field(description="Generated SQL")
    tables_used: list[str] = Field(default_factory=list, description="Tables used")
    columns_used: list[str] = Field(default_factory=list, description="Columns used")
    metrics_calculated: list[str] = Field(default_factory=list, description="Metrics calculated")
    joins_used: list[str] = Field(default_factory=list, description="Join types used")
    where_clauses: list[str] = Field(default_factory=list, description="Where conditions")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    explanation: str = Field(default="", description="Generation explanation")
    provider: str = Field(default="unknown", description="LLM provider used")
    model: str | None = Field(default=None, description="Model used")
    prompt_version: str | None = Field(default=None, description="Prompt version")
    sql_hash: str = Field(default="", description="SHA256 hash of SQL")


class SQLValidationResult(BaseModel):
    """Result of SQL validation."""

    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(description="Whether SQL is valid")
    status: ExecutionStatus = Field(description="Validation status")
    errors: list[SQLValidationErrorCategory] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    details: str = Field(default="", description="Detailed explanation")
    policy_checks: dict[str, bool] = Field(default_factory=dict, description="Policy check results")


class ExecutionResult(BaseModel):
    """Result of SQL execution."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(description="Whether execution succeeded")
    rows: list[dict[str, Any]] = Field(default_factory=list, description="Result rows")
    row_count: int = Field(default=0, description="Number of rows")
    columns: list[str] = Field(default_factory=list, description="Column names")
    column_types: dict[str, str] = Field(default_factory=dict, description="Column types")
    execution_time_ms: float = Field(default=0.0, description="Execution time")
    error: str | None = Field(default=None, description="Error message")
    error_category: SQLValidationErrorCategory | None = Field(default=None, description="Error category")
    is_truncated: bool = Field(default=False, description="Result was truncated")
    source_id: str | None = Field(default=None, description="Data source identifier")
    source_version: str | None = Field(default=None, description="Data source version")
    sql_hash: str = Field(default="", description="Hash of executed SQL")


class RepairAttempt(BaseModel):
    """A SQL repair attempt."""

    model_config = ConfigDict(extra="forbid")

    attempt_number: int = Field(ge=1, description="Attempt number")
    original_sql: str = Field(description="Original SQL")
    error: str = Field(description="Error that triggered repair")
    error_category: SQLValidationErrorCategory = Field(description="Error category")
    repaired_sql: str = Field(description="Repaired SQL")
    explanation: str = Field(description="Explanation of repair")
    success: bool = Field(default=False, description="Whether repair succeeded")
    validation_result: SQLValidationResult | None = None


class ResultValidationResult(BaseModel):
    """Result of executing SQL."""

    model_config = ConfigDict(extra="forbid")

    status: ExecutionStatus
    expected_columns: list[str] = Field(default_factory=list)
    actual_columns: list[str] = Field(default_factory=list)
    column_match: bool = True
    row_count: int = 0
    is_empty: bool = False
    null_count: int = 0
    duplicate_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    details: str = ""


class NL2SQLResult(BaseModel):
    """Complete result of NL2SQL pipeline."""

    model_config = ConfigDict(extra="forbid")

    # Input
    request: NL2SQLRequest

    # Processing
    query_lane: QueryLane = QueryLane.UNKNOWN
    logical_plan: LogicalQueryPlan | None = None
    generated_sql: GeneratedSQL | None = None
    validation: SQLValidationResult | None = None
    execution: ExecutionResult | None = None
    result_validation: ResultValidationResult | None = None
    repair_attempts: list[RepairAttempt] = Field(default_factory=list)

    # Output
    final_sql: str = ""
    final_status: ExecutionStatus = ExecutionStatus.REJECTED
    pipeline_duration_ms: float = 0.0

    # Provenance
    trace_id: str | None = None
    task_id: str | None = None

    @property
    def success(self) -> bool:
        """Whether the pipeline succeeded."""
        return self.final_status in (
            ExecutionStatus.VALID,
            ExecutionStatus.REPAIRABLE,  # Repaired and succeeded
        )

    @property
    def repair_count(self) -> int:
        """Number of repair attempts."""
        return len(self.repair_attempts)


# =============================================================================
# Provider Contracts
# =============================================================================


class SQLGeneratorProvider(BaseModel):
    """Abstract interface for SQL generator providers."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str = Field(description="Provider name")
    model_name: str = Field(description="Model name")

    def generate(
        self,
        question: str,
        schema_context: SchemaContext,
        logical_plan: LogicalQueryPlan,
        examples: list[GeneratedSQL],
        policy_constraints: dict[str, Any],
    ) -> GeneratedSQL:
        """Generate SQL from question and context.

        Args:
            question: Natural language question
            schema_context: Available schema
            logical_plan: Query plan
            examples: Approved SQL examples
            policy_constraints: Policy constraints

        Returns:
            Generated SQL

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError


class ExecutorProvider(BaseModel):
    """Abstract interface for SQL executor providers."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str = Field(default="unknown", description="Provider name")
    executor_type: str = Field(default="unknown", description="Executor type")
    executor_version: str = Field(default="1.0", description="Executor version")
    supports_explain: bool = Field(default=False, description="Supports EXPLAIN")
    supports_cancellation: bool = Field(default=False, description="Supports cancellation")

    def execute(
        self,
        sql: str,
        timeout_seconds: int = 30,
        max_rows: int = 10000,
    ) -> ExecutionResult:
        """Execute SQL and return results.

        Args:
            sql: SQL to execute
            timeout_seconds: Query timeout
            max_rows: Maximum rows to return

        Returns:
            Execution result

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError

    def explain(self, sql: str) -> dict[str, Any]:
        """Get query execution plan.

        Args:
            sql: SQL to explain

        Returns:
            Execution plan

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError
