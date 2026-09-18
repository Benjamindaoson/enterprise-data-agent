"""Tests for NL2SQL contracts."""

import pytest
from datetime import date, datetime

from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    QueryLane,
    ExecutionStatus,
    TableInfo,
    ColumnInfo,
    JoinInfo,
    SchemaContext,
    NL2SQLRequest,
    LogicalQueryPlan,
    GeneratedSQL,
    SQLValidationResult,
    ExecutionResult,
    RepairAttempt,
    ResultValidationResult,
    NL2SQLResult,
)


class TestEnums:
    """Test enum values."""

    def test_sql_validation_error_category_values(self):
        """Test SQLValidationErrorCategory enum values."""
        assert SQLValidationErrorCategory.SYNTAX_ERROR.value == "syntax_error"
        assert SQLValidationErrorCategory.UNKNOWN_TABLE.value == "unknown_table"
        assert SQLValidationErrorCategory.UNKNOWN_COLUMN.value == "unknown_column"
        assert SQLValidationErrorCategory.INVALID_JOIN.value == "invalid_join"
        assert SQLValidationErrorCategory.AGGREGATION_ERROR.value == "aggregation_error"
        assert SQLValidationErrorCategory.GRAIN_ERROR.value == "grain_error"
        assert SQLValidationErrorCategory.COMPLEXITY_EXCEEDED.value == "complexity_exceeded"
        assert SQLValidationErrorCategory.PERMISSION_DENIED.value == "permission_denied"
        assert SQLValidationErrorCategory.SECURITY_POLICY.value == "security_policy"
        assert SQLValidationErrorCategory.INVALID_METRIC_FORMULA.value == "invalid_metric_formula"
        assert SQLValidationErrorCategory.EMPTY_UNEXPECTED_RESULT.value == "empty_unexpected_result"
        assert SQLValidationErrorCategory.SEMANTIC_MISMATCH.value == "semantic_mismatch"

    def test_query_lane_values(self):
        """Test QueryLane enum values."""
        assert QueryLane.DETERMINISTIC.value == "deterministic"
        assert QueryLane.GOVERNED_NL2SQL.value == "governed_nl2sql"
        assert QueryLane.UNKNOWN.value == "unknown"

    def test_execution_status_values(self):
        """Test ExecutionStatus enum values."""
        assert ExecutionStatus.VALID.value == "VALID"
        assert ExecutionStatus.REPAIRABLE.value == "REPAIRABLE"
        assert ExecutionStatus.REJECTED.value == "REJECTED"
        assert ExecutionStatus.NEEDS_CLARIFICATION.value == "NEEDS_CLARIFICATION"
        assert ExecutionStatus.EXECUTION_ERROR.value == "EXECUTION_ERROR"
        assert ExecutionStatus.TIMEOUT_ERROR.value == "TIMEOUT_ERROR"


class TestTableInfo:
    """Test TableInfo dataclass."""

    def test_table_info_creation(self):
        """Test TableInfo creation."""
        table = TableInfo(
            name="orders",
            description="Customer orders table",
            is_sensitive=False,
        )
        assert table.name == "orders"
        assert table.description == "Customer orders table"
        assert table.is_sensitive is False

    def test_table_info_with_columns(self):
        """Test TableInfo with columns."""
        columns = [
            ColumnInfo(name="order_id", data_type="VARCHAR", description="Primary key"),
            ColumnInfo(name="amount", data_type="DECIMAL", description="Order amount"),
        ]
        table = TableInfo(
            name="orders",
            columns=columns,
        )
        assert len(table.columns) == 2
        assert table.columns[0].name == "order_id"


class TestColumnInfo:
    """Test ColumnInfo dataclass."""

    def test_column_info_creation(self):
        """Test ColumnInfo creation."""
        col = ColumnInfo(
            name="order_id",
            data_type="VARCHAR",
            description="Primary key",
        )
        assert col.name == "order_id"
        assert col.data_type == "VARCHAR"
        assert col.is_sensitive is False

    def test_column_info_sensitive(self):
        """Test sensitive column."""
        col = ColumnInfo(
            name="password_hash",
            data_type="VARCHAR",
            is_sensitive=True,
        )
        assert col.is_sensitive is True


class TestJoinInfo:
    """Test JoinInfo dataclass."""

    def test_join_info_creation(self):
        """Test JoinInfo creation."""
        join = JoinInfo(
            from_table="orders",
            from_column="customer_id",
            to_table="customers",
            to_column="id",
            join_type="LEFT",
        )
        assert join.from_table == "orders"
        assert join.to_table == "customers"
        assert join.join_type == "LEFT"


class TestSchemaContext:
    """Test SchemaContext dataclass."""

    def test_schema_context_creation(self):
        """Test SchemaContext creation."""
        table = TableInfo(name="orders")
        join = JoinInfo(
            from_table="orders",
            from_column="customer_id",
            to_table="customers",
            to_column="id",
        )

        schema = SchemaContext(
            tables={"orders": table},
            joins=[join],
        )

        assert "orders" in schema.tables
        assert len(schema.joins) == 1


class TestNL2SQLRequest:
    """Test NL2SQLRequest dataclass."""

    def test_request_creation(self):
        """Test NL2SQLRequest creation."""
        request = NL2SQLRequest(
            question="What is total revenue?",
            domain="finance",
        )
        assert request.question == "What is total revenue?"
        assert request.domain == "finance"
        assert request.time_range_start is None
        assert request.time_range_end is None

    def test_request_with_time_range(self):
        """Test request with time range."""
        request = NL2SQLRequest(
            question="Revenue last year",
            domain="finance",
            time_range_start=date(2023, 1, 1),
            time_range_end=date(2023, 12, 31),
        )
        assert request.time_range_start == date(2023, 1, 1)
        assert request.time_range_end == date(2023, 12, 31)

    def test_request_with_user_context(self):
        """Test request with user context."""
        request = NL2SQLRequest(
            question="Show revenue",
            domain="finance",
            user_id="user123",
            user_roles=["viewer"],
        )
        assert request.user_id == "user123"
        assert "viewer" in request.user_roles


class TestLogicalQueryPlan:
    """Test LogicalQueryPlan dataclass."""

    def test_plan_creation(self):
        """Test LogicalQueryPlan creation."""
        plan = LogicalQueryPlan(
            purpose="aggregation",
            metrics=["revenue"],
            dimensions=["region"],
        )
        assert plan.purpose == "aggregation"
        assert plan.metrics == ["revenue"]
        assert plan.dimensions == ["region"]

    def test_plan_with_time_range(self):
        """Test plan with time range."""
        plan = LogicalQueryPlan(
            purpose="trend_analysis",
            time_range_start=date(2023, 1, 1),
            time_range_end=date(2023, 12, 31),
        )
        assert plan.time_range_start == date(2023, 1, 1)
        assert plan.time_range_end == date(2023, 12, 31)


class TestGeneratedSQL:
    """Test GeneratedSQL dataclass."""

    def test_generated_sql_creation(self):
        """Test GeneratedSQL creation."""
        sql = GeneratedSQL(
            sql="SELECT SUM(revenue) FROM orders",
            tables_used=["orders"],
            columns_used=["revenue"],
            confidence=0.95,
        )
        assert sql.sql == "SELECT SUM(revenue) FROM orders"
        assert sql.confidence == 0.95
        assert sql.tables_used == ["orders"]


class TestSQLValidationResult:
    """Test SQLValidationResult dataclass."""

    def test_valid_result(self):
        """Test valid validation result."""
        result = SQLValidationResult(
            is_valid=True,
            status=ExecutionStatus.VALID,
        )
        assert result.is_valid is True
        assert result.status == ExecutionStatus.VALID

    def test_invalid_result_with_errors(self):
        """Test invalid result with errors."""
        result = SQLValidationResult(
            is_valid=False,
            status=ExecutionStatus.REJECTED,
            errors=[SQLValidationErrorCategory.SYNTAX_ERROR],
            warnings=["Warning: no LIMIT clause"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_success_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            execution_time_ms=150,
            row_count=10,
            columns=["id", "name"],
        )
        assert result.success is True
        assert result.row_count == 10
        assert len(result.columns) == 2

    def test_error_result(self):
        """Test error execution result."""
        result = ExecutionResult(
            success=False,
            error="Table not found",
            error_category=SQLValidationErrorCategory.UNKNOWN_TABLE,
        )
        assert result.success is False
        assert result.error_category == SQLValidationErrorCategory.UNKNOWN_TABLE


class TestRepairAttempt:
    """Test RepairAttempt dataclass."""

    def test_repair_attempt_creation(self):
        """Test RepairAttempt creation."""
        attempt = RepairAttempt(
            attempt_number=1,
            original_sql="SELECT * FROM orders",
            error="No LIMIT clause",
            error_category=SQLValidationErrorCategory.COMPLEXITY_EXCEEDED,
            repaired_sql="SELECT * FROM orders LIMIT 1000",
            explanation="Added LIMIT clause",
            success=True,
        )
        assert attempt.original_sql == "SELECT * FROM orders"
        assert attempt.attempt_number == 1
        assert attempt.success is True


class TestNL2SQLResult:
    """Test NL2SQLResult dataclass."""

    def test_success_result(self):
        """Test successful NL2SQL result."""
        request = NL2SQLRequest(
            question="Show me something",
            domain="finance",
        )
        generated = GeneratedSQL(sql="SELECT 1", confidence=0.9)
        execution = ExecutionResult(
            success=True,
            execution_time_ms=100,
            row_count=1,
            columns=["col1"],
        )

        nl2sql_result = NL2SQLResult(
            request=request,
            generated_sql=generated,
            execution=execution,
            final_status=ExecutionStatus.VALID,
        )

        assert nl2sql_result.final_status == ExecutionStatus.VALID
        assert nl2sql_result.generated_sql is not None

    def test_error_result(self):
        """Test error NL2SQL result."""
        request = NL2SQLRequest(
            question="Show me something",
            domain="finance",
        )

        nl2sql_result = NL2SQLResult(
            request=request,
            final_status=ExecutionStatus.REJECTED,
        )

        assert nl2sql_result.final_status == ExecutionStatus.REJECTED
