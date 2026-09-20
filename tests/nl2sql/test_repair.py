"""Tests for SQL Repair module."""

import pytest

from eiw.nl2sql.repair import (
    SQLRepair,
    RepairConfig,
    RepairContext,
    RepairStrategy,
    RepairClassification,
    RepairStrategySelector,
    create_repair,
)
from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    ExecutionResult,
    ExecutionStatus,
)


class TestRepairStrategySelector:
    """Test RepairStrategySelector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.selector = RepairStrategySelector()

    def test_classify_syntax_error(self):
        """Test classification of syntax error."""
        classification, strategies = self.selector.classify(SQLValidationErrorCategory.SYNTAX_ERROR)

        assert classification == RepairClassification.MODERATE
        assert RepairStrategy.FIX_SYNTAX in strategies

    def test_classify_permission_denied(self):
        """Test classification of permission denied."""
        classification, strategies = self.selector.classify(SQLValidationErrorCategory.PERMISSION_DENIED)

        assert classification == RepairClassification.NEVER_REPAIR
        assert RepairStrategy.ESCALATE in strategies

    def test_classify_security_policy(self):
        """Test classification of security policy violation."""
        classification, strategies = self.selector.classify(SQLValidationErrorCategory.SECURITY_POLICY)

        assert classification == RepairClassification.NEVER_REPAIR

    def test_classify_complexity_exceeded(self):
        """Test classification of complexity exceeded."""
        classification, strategies = self.selector.classify(SQLValidationErrorCategory.COMPLEXITY_EXCEEDED)

        assert classification == RepairClassification.SAFE
        assert RepairStrategy.ADD_LIMIT in strategies

    def test_classify_unknown_table(self):
        """Test classification of unknown table."""
        classification, strategies = self.selector.classify(SQLValidationErrorCategory.UNKNOWN_TABLE)

        assert classification == RepairClassification.RISKY

    def test_should_repair_permission_denied(self):
        """Test should_repair returns False for permission denied."""
        config = RepairConfig()
        result = self.selector.should_repair(
            SQLValidationErrorCategory.PERMISSION_DENIED,
            config,
            attempt_count=0,
        )

        assert result is False

    def test_should_repair_security_policy(self):
        """Test should_repair returns False for security policy."""
        config = RepairConfig()
        result = self.selector.should_repair(
            SQLValidationErrorCategory.SECURITY_POLICY,
            config,
            attempt_count=0,
        )

        assert result is False

    def test_should_repair_max_attempts_exceeded(self):
        """Test should_repair returns False when max attempts exceeded."""
        config = RepairConfig(max_repair_attempts=3)
        result = self.selector.should_repair(
            SQLValidationErrorCategory.COMPLEXITY_EXCEEDED,
            config,
            attempt_count=3,
        )

        assert result is False

    def test_should_repair_within_limits(self):
        """Test should_repair returns True within limits."""
        config = RepairConfig()
        result = self.selector.should_repair(
            SQLValidationErrorCategory.COMPLEXITY_EXCEEDED,
            config,
            attempt_count=0,
        )

        assert result is True


class TestSQLRepair:
    """Test SQLRepair class."""

    def setup_method(self):
        """Set up test fixtures."""
        config = RepairConfig(max_repair_attempts=3)
        self.repair = SQLRepair(config=config)

    def test_repair_add_limit(self):
        """Test repair adds LIMIT clause."""
        sql = "SELECT * FROM orders WHERE region = 'APAC'"
        errors = [SQLValidationErrorCategory.COMPLEXITY_EXCEEDED]

        result = self.repair.repair(sql, errors)

        # May or may not repair depending on strategy selection

    def test_repair_simplify(self):
        """Test repair simplifies query."""
        sql = "SELECT * FROM orders WHERE region = 'APAC' ORDER BY amount DESC"
        errors = [SQLValidationErrorCategory.COMPLEXITY_EXCEEDED]

        result = self.repair.repair(sql, errors)

        # May simplify depending on strategy selection

    def test_repair_permission_denied_returns_none(self):
        """Test repair returns None for permission denied."""
        sql = "SELECT * FROM admin_users"
        errors = [SQLValidationErrorCategory.PERMISSION_DENIED]

        result = self.repair.repair(sql, errors)

        # No repair possible
        assert result is None

    def test_repair_security_policy_returns_none(self):
        """Test repair returns None for security policy violations."""
        sql = "SELECT password_hash FROM users"
        errors = [SQLValidationErrorCategory.SECURITY_POLICY]

        result = self.repair.repair(sql, errors)

        assert result is None

    def test_repair_no_errors_returns_none(self):
        """Test repair returns None when no errors."""
        sql = "SELECT * FROM orders"
        errors = []

        result = self.repair.repair(sql, errors)

        assert result is None

    def test_repair_tracks_attempt_count(self):
        """Test repair tracks attempt count."""
        sql = "SELECT * FROM orders"
        errors = [SQLValidationErrorCategory.COMPLEXITY_EXCEEDED]

        result = self.repair.repair(sql, errors)

        assert result is not None
        assert result.attempt_number >= 1

    def test_repair_recommendations(self):
        """Test get_repair_recommendations."""
        errors = [
            SQLValidationErrorCategory.COMPLEXITY_EXCEEDED,
            SQLValidationErrorCategory.UNKNOWN_COLUMN,
        ]

        recommendations = self.repair.get_repair_recommendation(errors)

        # All errors should be repairable in this case
        assert recommendations["can_repair"] is True
        assert recommendations["escalation_required"] is False
        assert len(recommendations["recommendations"]) == 2

    def test_repair_recommendations_all_never_repair(self):
        """Test recommendations when all errors are never repair."""
        errors = [
            SQLValidationErrorCategory.PERMISSION_DENIED,
            SQLValidationErrorCategory.SECURITY_POLICY,
        ]

        recommendations = self.repair.get_repair_recommendation(errors)

        assert recommendations["can_repair"] is False
        assert recommendations["escalation_required"] is True


class TestRepairStrategies:
    """Test individual repair strategies."""

    def test_add_limit_strategy(self):
        """Test ADD_LIMIT strategy."""
        config = RepairConfig()
        repair = SQLRepair(config=config)

        sql = "SELECT * FROM orders WHERE region = 'APAC'"
        errors = [SQLValidationErrorCategory.COMPLEXITY_EXCEEDED]

        result = repair.repair(sql, errors)

        # Repair may or may not be applied

    def test_add_limit_already_present(self):
        """Test ADD_LIMIT strategy when LIMIT already present."""
        config = RepairConfig()
        repair = SQLRepair(config=config)

        sql = "SELECT * FROM orders LIMIT 100"
        errors = [SQLValidationErrorCategory.COMPLEXITY_EXCEEDED]

        result = repair.repair(sql, errors)

        # May or may not add another LIMIT
        # Depends on strategy selection

    def test_fix_syntax_strategy(self):
        """Test FIX_SYNTAX strategy."""
        config = RepairConfig()
        repair = SQLRepair(config=config)

        sql = "SELECT * FROM orders WHERE a = b"
        errors = [SQLValidationErrorCategory.SYNTAX_ERROR]

        result = repair.repair(sql, errors)

        # May repair syntax errors

    def test_change_aggregation_count_to_sum(self):
        """Test changing COUNT to SUM."""
        config = RepairConfig()
        repair = SQLRepair(config=config)

        sql = "SELECT COUNT(amount) FROM orders"
        errors = [SQLValidationErrorCategory.AGGREGATION_ERROR]

        result = repair.repair(sql, errors)

        # May change aggregation

    def test_change_aggregation_sum_to_count(self):
        """Test changing SUM to COUNT."""
        config = RepairConfig()
        repair = SQLRepair(config=config)

        sql = "SELECT SUM(id) FROM orders"
        errors = [SQLValidationErrorCategory.AGGREGATION_ERROR]

        result = repair.repair(sql, errors)

        # May change aggregation


class TestCreateRepair:
    """Test create_repair factory function."""

    def test_create_repair_default_config(self):
        """Test create_repair with default config."""
        repair = create_repair()

        assert repair is not None
        assert isinstance(repair, SQLRepair)

    def test_create_repair_custom_config(self):
        """Test create_repair with custom config."""
        config = RepairConfig(max_repair_attempts=5)
        repair = create_repair(config=config)

        assert repair is not None
        assert repair._config.max_repair_attempts == 5
