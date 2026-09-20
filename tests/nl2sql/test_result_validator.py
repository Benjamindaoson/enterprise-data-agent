"""Tests for Result Validator module."""

import pytest
from datetime import date, datetime

from eiw.nl2sql.result_validator import (
    ResultValidator,
    ResultValidationConfig,
)
from eiw.nl2sql.contracts import (
    ExecutionResult,
    ExecutionStatus,
    SQLValidationErrorCategory,
)


class TestResultValidator:
    """Test ResultValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ResultValidator()

    def test_validate_success(self):
        """Test successful result validation."""
        result = ExecutionResult(
            success=True,
            execution_time_ms=100,
            row_count=3,
            rows=[
                {"id": 1, "name": "Product A", "amount": 100.0},
                {"id": 2, "name": "Product B", "amount": 200.0},
                {"id": 3, "name": "Product C", "amount": 150.0},
            ],
            columns=["id", "name", "amount"],
        )

        validation = self.validator.validate(result)

        assert validation.status == ExecutionStatus.VALID
        assert validation.row_count == 3
        assert validation.actual_columns == ["id", "name", "amount"]

    def test_validate_empty_result_not_allowed(self):
        """Test empty result when not allowed."""
        result = ExecutionResult(
            success=True,
            execution_time_ms=50,
            row_count=0,
            rows=[],
            columns=["id", "name"],
        )

        validation = self.validator.validate(result)

        assert validation.is_empty is True
        assert "empty" in validation.details.lower()

    def test_validate_empty_result_allowed(self):
        """Test empty result when allowed."""
        validator = ResultValidator(ResultValidationConfig(allow_empty=True))

        result = ExecutionResult(
            success=True,
            execution_time_ms=50,
            row_count=0,
            rows=[],
            columns=["id", "name"],
        )

        validation = validator.validate(result)

        # Empty is allowed but should be noted
        assert validation.is_empty is True

    def test_validate_column_types(self):
        """Test column type validation."""
        result = ExecutionResult(
            success=True,
            row_count=2,
            rows=[
                {"id": 1, "amount": 100.5},
                {"id": 2, "amount": 200.5},
            ],
            columns=["id", "amount"],
        )

        validation = self.validator.validate(
            result,
            expected_types={"id": "integer", "amount": "float"},
        )

        assert validation.status == ExecutionStatus.VALID

    def test_validate_column_type_mismatch(self):
        """Test column type mismatch detection."""
        result = ExecutionResult(
            success=True,
            row_count=2,
            rows=[
                {"id": "not a number", "amount": 100.5},
                {"id": "also not a number", "amount": 200.5},
            ],
            columns=["id", "amount"],
        )

        validation = self.validator.validate(
            result,
            expected_types={"id": "integer", "amount": "float"},
        )

        # Should detect type mismatch - validation should fail
        assert validation.status == ExecutionStatus.REJECTED
        assert "id" in validation.details.lower()

    def test_validate_null_values(self):
        """Test null value handling."""
        result = ExecutionResult(
            success=True,
            row_count=3,
            rows=[
                {"id": 1, "amount": 100.0},
                {"id": 2, "amount": None},
                {"id": 3, "amount": 300.0},
            ],
            columns=["id", "amount"],
        )

        validation = self.validator.validate(result)

        assert validation.status == ExecutionStatus.VALID
        # Check for warnings about null values (we just verify the validation passes)

    def test_validate_excessive_nulls(self):
        """Test excessive null value warning."""
        validator = ResultValidator(ResultValidationConfig(max_null_ratio=0.3))

        result = ExecutionResult(
            success=True,
            row_count=10,
            rows=[{"id": i, "amount": None} for i in range(10)],
            columns=["id", "amount"],
        )

        validation = validator.validate(result)

        # Should have warning about high null ratio
        assert any("null" in w.lower() for w in validation.warnings)

    def test_validate_duplicates_detected(self):
        """Test duplicate detection."""
        result = ExecutionResult(
            success=True,
            row_count=4,
            rows=[
                {"id": 1, "name": "A"},
                {"id": 2, "name": "B"},
                {"id": 1, "name": "A"},  # Duplicate
                {"id": 3, "name": "C"},
            ],
            columns=["id", "name"],
        )

        validation = self.validator.validate(result)

        assert any("duplicate" in w.lower() for w in validation.warnings)

    def test_validate_row_count_min(self):
        """Test minimum row count validation."""
        validator = ResultValidator(
            ResultValidationConfig(expected_row_count_min=5)
        )

        result = ExecutionResult(
            success=True,
            row_count=3,
            rows=[{"id": i} for i in range(3)],
            columns=["id"],
        )

        validation = validator.validate(result)

        assert any("minimum" in w.lower() for w in validation.warnings)

    def test_validate_row_count_max(self):
        """Test maximum row count validation."""
        validator = ResultValidator(
            ResultValidationConfig(expected_row_count_max=2)
        )

        result = ExecutionResult(
            success=True,
            row_count=5,
            rows=[{"id": i} for i in range(5)],
            columns=["id"],
        )

        validation = validator.validate(result)

        assert any("maximum" in w.lower() for w in validation.warnings)

    def test_validate_column_names(self):
        """Test column name validation."""
        result = ExecutionResult(
            success=True,
            row_count=1,
            rows=[{"id": 1, "name": "test"}],
            columns=["id", "name"],
        )

        validation = self.validator.validate(
            result,
            expected_columns=["id", "full_name"],  # Different column
        )

        assert len(validation.warnings) > 0

    def test_validate_column_count_mismatch(self):
        """Test column count mismatch."""
        result = ExecutionResult(
            success=True,
            row_count=1,
            rows=[{"id": 1, "name": "test"}],
            columns=["id", "name"],
        )

        validation = self.validator.validate(
            result,
            expected_columns=["id", "name", "extra"],  # 3 columns expected
        )

        assert not validation.column_match

    def test_validate_all_null_column(self):
        """Test all-null column detection."""
        result = ExecutionResult(
            success=True,
            row_count=3,
            rows=[
                {"id": 1, "value": None},
                {"id": 2, "value": None},
                {"id": 3, "value": None},
            ],
            columns=["id", "value"],
        )

        validation = self.validator.validate(result)

        # All null column should cause validation to fail
        # The details field should contain the error message
        assert validation.status == ExecutionStatus.REJECTED
        assert "value" in validation.details.lower()

    def test_validate_no_variance_column(self):
        """Test no-variance column detection."""
        result = ExecutionResult(
            success=True,
            row_count=5,
            rows=[
                {"id": 1, "constant": "same"},
                {"id": 2, "constant": "same"},
                {"id": 3, "constant": "same"},
                {"id": 4, "constant": "same"},
                {"id": 5, "constant": "same"},
            ],
            columns=["id", "constant"],
        )

        validation = self.validator.validate(result)

        # No variance column should cause validation to fail
        assert validation.status == ExecutionStatus.REJECTED
        assert "constant" in validation.details.lower()

    def test_validate_time_grain_daily(self):
        """Test daily time grain validation."""
        result = ExecutionResult(
            success=True,
            row_count=3,
            rows=[
                {"order_date": date(2024, 1, 1), "amount": 100.0},
                {"order_date": date(2024, 1, 2), "amount": 200.0},
                {"order_date": date(2024, 1, 3), "amount": 150.0},
            ],
            columns=["order_date", "amount"],
        )

        validation = self.validator.validate(
            result,
            time_grain="DAILY",
        )

        # Should pass for daily grain with proper dates

    def test_validate_time_grain_monthly(self):
        """Test monthly time grain validation."""
        result = ExecutionResult(
            success=True,
            row_count=2,
            rows=[
                {"order_date": date(2024, 1, 15), "amount": 100.0},
                {"order_date": date(2024, 2, 15), "amount": 200.0},
            ],
            columns=["order_date", "amount"],
        )

        validation = self.validator.validate(
            result,
            time_grain="MONTHLY",
        )

        # Should pass for monthly grain


class TestValidateSchemaMatch:
    """Test schema match validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ResultValidator()

    def test_schema_match_success(self):
        """Test successful schema match."""
        result = ExecutionResult(
            success=True,
            row_count=2,
            rows=[
                {"id": 1, "amount": 100.5},
                {"id": 2, "amount": 200.5},
            ],
            columns=["id", "amount"],
        )

        is_valid, errors = self.validator.validate_schema_match(
            result,
            {"id": "integer", "amount": "number"},
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_schema_match_missing_column(self):
        """Test schema match with missing column."""
        result = ExecutionResult(
            success=True,
            row_count=2,
            rows=[
                {"id": 1, "amount": 100.5},
                {"id": 2, "amount": 200.5},
            ],
            columns=["id", "amount"],
        )

        is_valid, errors = self.validator.validate_schema_match(
            result,
            {"id": "integer", "amount": "number", "missing": "string"},
        )

        assert is_valid is False
        assert any("missing" in e.lower() for e in errors)

    def test_schema_match_type_mismatch(self):
        """Test schema match with type mismatch."""
        result = ExecutionResult(
            success=True,
            row_count=2,
            rows=[
                {"id": "not int", "amount": 100.5},
                {"id": "also not int", "amount": 200.5},
            ],
            columns=["id", "amount"],
        )

        is_valid, errors = self.validator.validate_schema_match(
            result,
            {"id": "integer", "amount": "number"},
        )

        assert is_valid is False

    def test_schema_match_column_count_mismatch(self):
        """Test schema match with column count mismatch."""
        result = ExecutionResult(
            success=True,
            row_count=2,
            rows=[
                {"id": 1, "amount": 100.5},
                {"id": 2, "amount": 200.5},
            ],
            columns=["id", "amount"],
        )

        is_valid, errors = self.validator.validate_schema_match(
            result,
            {"id": "integer"},  # Only 1 column expected
        )

        assert is_valid is False


class TestLooksLikeDate:
    """Test date detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ResultValidator()

    def test_iso_date_format(self):
        """Test ISO date format detection."""
        assert self.validator._looks_like_date("2024-01-15") is True
        assert self.validator._looks_like_date("2024-12-31") is True

    def test_iso_datetime_format(self):
        """Test ISO datetime format detection."""
        assert self.validator._looks_like_date("2024-01-15T10:30:00") is True
        assert self.validator._looks_like_date("2024-01-15 10:30:00") is True

    def test_us_date_format(self):
        """Test US date format detection."""
        assert self.validator._looks_like_date("01/15/2024") is True
        assert self.validator._looks_like_date("12/31/2024") is True

    def test_not_date(self):
        """Test non-date strings."""
        assert self.validator._looks_like_date("hello world") is False
        assert self.validator._looks_like_date("abc123") is False
        assert self.validator._looks_like_date("12345") is False
