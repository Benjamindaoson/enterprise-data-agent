"""Tests for SQL Policy Validator."""

import pytest

from eiw.nl2sql.policy import (
    SQLPolicyValidator,
    PolicyContext,
    check_sql_security_bypass_attempts,
)
from eiw.nl2sql.parser import ParsedSQL
from eiw.nl2sql.contracts import (
    SQLValidationErrorCategory,
    ExecutionStatus,
    SchemaContext,
    TableInfo,
    ColumnInfo,
)


class TestSQLPolicyValidator:
    """Test SQLPolicyValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SQLPolicyValidator()

    def _create_basic_parsed_sql(self, sql: str) -> ParsedSQL:
        """Helper to create basic ParsedSQL."""
        return ParsedSQL(
            original_sql=sql,
            parsed=None,
            tables=["orders"],
            columns=["order_id", "amount"],
            joins=[],
            subqueries=[],
            ctes=[],
            functions=[],
            has_union=False,
            has_group_by=False,
            has_order_by=False,
            has_limit=False,
            statement_count=1,
        )

    def test_check_forbidden_operations_none(self):
        """Test no forbidden operations detected."""
        sql = "SELECT * FROM orders WHERE amount > 100"
        result = self.validator._check_forbidden_operations(sql)

        assert len(result) == 0

    def test_check_forbidden_operations_insert(self):
        """Test INSERT detected."""
        sql = "INSERT INTO orders (id) VALUES (1)"
        result = self.validator._check_forbidden_operations(sql)

        assert SQLValidationErrorCategory.SECURITY_POLICY in result

    def test_check_forbidden_operations_update(self):
        """Test UPDATE detected."""
        sql = "UPDATE orders SET amount = 100"
        result = self.validator._check_forbidden_operations(sql)

        assert SQLValidationErrorCategory.SECURITY_POLICY in result

    def test_check_forbidden_operations_delete(self):
        """Test DELETE detected."""
        sql = "DELETE FROM orders WHERE id = 1"
        result = self.validator._check_forbidden_operations(sql)

        assert SQLValidationErrorCategory.SECURITY_POLICY in result

    def test_check_forbidden_operations_drop(self):
        """Test DROP detected."""
        sql = "DROP TABLE orders"
        result = self.validator._check_forbidden_operations(sql)

        assert SQLValidationErrorCategory.SECURITY_POLICY in result

    def test_check_forbidden_operations_truncate(self):
        """Test TRUNCATE detected."""
        sql = "TRUNCATE TABLE orders"
        result = self.validator._check_forbidden_operations(sql)

        assert SQLValidationErrorCategory.SECURITY_POLICY in result

    def test_check_table_access_allowed(self):
        """Test table access allowed."""
        parsed_sql = self._create_basic_parsed_sql("SELECT * FROM orders")
        policy_context = PolicyContext(
            user_roles=["viewer"],
            allowed_tables=["orders", "customers"],
        )

        result = self.validator._check_table_access(parsed_sql, policy_context)

        assert len(result) == 0

    def test_check_table_access_denied(self):
        """Test table access denied for unknown table."""
        parsed_sql = ParsedSQL(
            original_sql="SELECT * FROM unknown_table",
            parsed=None,
            tables=["unknown_table"],  # Table not in allowed list
            columns=["id"],
            joins=[],
            subqueries=[],
            ctes=[],
            functions=[],
            has_union=False,
            has_group_by=False,
            has_order_by=False,
            has_limit=False,
            statement_count=1,
        )
        policy_context = PolicyContext(
            user_roles=["viewer"],
            allowed_tables=["orders", "customers"],
        )

        result = self.validator._check_table_access(parsed_sql, policy_context)

        assert SQLValidationErrorCategory.UNKNOWN_TABLE in result

    def test_check_table_access_admin_table(self):
        """Test admin table access requires admin role."""
        parsed_sql = ParsedSQL(
            original_sql="SELECT * FROM admin_users",
            parsed=None,
            tables=["admin_users"],
            columns=["id", "username"],
            joins=[],
            subqueries=[],
            ctes=[],
            functions=[],
            has_union=False,
            has_group_by=False,
            has_order_by=False,
            has_limit=False,
            statement_count=1,
        )
        policy_context = PolicyContext(
            user_roles=["viewer"],  # Not admin
            denied_tables=None,
        )

        result = self.validator._check_table_access(parsed_sql, policy_context)

        assert SQLValidationErrorCategory.PERMISSION_DENIED in result

    def test_check_table_access_admin_role(self):
        """Test admin can access admin tables."""
        parsed_sql = ParsedSQL(
            original_sql="SELECT * FROM admin_users",
            parsed=None,
            tables=["admin_users"],
            columns=["id", "username"],
            joins=[],
            subqueries=[],
            ctes=[],
            functions=[],
            has_union=False,
            has_group_by=False,
            has_order_by=False,
            has_limit=False,
            statement_count=1,
        )
        policy_context = PolicyContext(
            user_roles=["admin"],  # Admin role
            denied_tables=None,
        )

        result = self.validator._check_table_access(parsed_sql, policy_context)

        assert SQLValidationErrorCategory.PERMISSION_DENIED not in result

    def test_check_column_access_denied(self):
        """Test column access denied."""
        parsed_sql = ParsedSQL(
            original_sql="SELECT password_hash FROM users",
            parsed=None,
            tables=["users"],
            columns=["password_hash"],
            joins=[],
            subqueries=[],
            ctes=[],
            functions=[],
            has_union=False,
            has_group_by=False,
            has_order_by=False,
            has_limit=False,
            statement_count=1,
        )
        policy_context = PolicyContext(
            user_roles=["viewer"],
            denied_columns=["password_hash"],
        )

        result = self.validator._check_column_access(parsed_sql, None, policy_context)

        assert SQLValidationErrorCategory.PERMISSION_DENIED in result

    def test_check_sensitive_columns_password(self):
        """Test sensitive column detection for password."""
        parsed_sql = ParsedSQL(
            original_sql="SELECT password_hash FROM users",
            parsed=None,
            tables=["users"],
            columns=["password_hash"],
            joins=[],
            subqueries=[],
            ctes=[],
            functions=[],
            has_union=False,
            has_group_by=False,
            has_order_by=False,
            has_limit=False,
            statement_count=1,
        )
        schema = SchemaContext(
            tables={"users": TableInfo(name="users", columns=[
                ColumnInfo(name="password_hash", data_type="VARCHAR", is_sensitive=True),
            ])},
            joins=[],
        )

        result = self.validator._check_sensitive_columns(parsed_sql, schema)

        assert SQLValidationErrorCategory.SECURITY_POLICY in result

    def test_check_sensitive_columns_api_key(self):
        """Test sensitive column detection for api_key."""
        parsed_sql = ParsedSQL(
            original_sql="SELECT api_key FROM api_keys",
            parsed=None,
            tables=["api_keys"],
            columns=["api_key"],
            joins=[],
            subqueries=[],
            ctes=[],
            functions=[],
            has_union=False,
            has_group_by=False,
            has_order_by=False,
            has_limit=False,
            statement_count=1,
        )
        schema = SchemaContext(
            tables={"api_keys": TableInfo(name="api_keys", columns=[
                ColumnInfo(name="api_key", data_type="VARCHAR", is_sensitive=True),
            ])},
            joins=[],
        )

        result = self.validator._check_sensitive_columns(parsed_sql, schema)

        assert SQLValidationErrorCategory.SECURITY_POLICY in result

    def test_check_complexity_within_limit(self):
        """Test complexity within limit."""
        parsed_sql = self._create_basic_parsed_sql("SELECT * FROM orders")
        parsed_sql.tables = ["orders"]
        parsed_sql.joins = []
        policy_context = PolicyContext(
            user_roles=["viewer"],
            max_complexity=10,
        )

        result = self.validator._check_complexity(parsed_sql, policy_context)

        assert len(result) == 0

    def test_check_complexity_exceeded(self):
        """Test complexity exceeded."""
        parsed_sql = self._create_basic_parsed_sql("SELECT * FROM orders")
        parsed_sql.tables = ["t1", "t2", "t3", "t4", "t5"]
        parsed_sql.joins = ["j1", "j2", "j3", "j4"]
        parsed_sql.subqueries = ["s1", "s2"]
        parsed_sql.ctes = ["c1", "c2"]
        parsed_sql.has_union = True
        policy_context = PolicyContext(
            user_roles=["viewer"],
            max_complexity=10,
        )

        result = self.validator._check_complexity(parsed_sql, policy_context)

        assert SQLValidationErrorCategory.COMPLEXITY_EXCEEDED in result

    def test_check_row_limit_has_limit(self):
        """Test row limit check when LIMIT present."""
        parsed_sql = self._create_basic_parsed_sql("SELECT * FROM orders LIMIT 100")
        parsed_sql.has_limit = True

        result = self.validator._check_row_limit(parsed_sql, PolicyContext(user_roles=["viewer"]))

        assert len(result) == 0

    def test_check_row_limit_no_limit(self):
        """Test row limit warning when no LIMIT."""
        parsed_sql = self._create_basic_parsed_sql("SELECT * FROM orders")
        parsed_sql.has_limit = False

        result = self.validator._check_row_limit(parsed_sql, PolicyContext(user_roles=["viewer"]))

        assert len(result) > 0
        assert "LIMIT" in result[0]

    def test_validate_full_pass(self):
        """Test full validation passes."""
        parsed_sql = self._create_basic_parsed_sql("SELECT order_id, amount FROM orders WHERE amount > 100")
        schema = SchemaContext(
            tables={"orders": TableInfo(name="orders", columns=[
                ColumnInfo(name="order_id", data_type="VARCHAR"),
                ColumnInfo(name="amount", data_type="DECIMAL"),
            ])},
            joins=[],
        )
        policy_context = PolicyContext(
            user_roles=["viewer"],
            allowed_tables=["orders"],
            allowed_columns=["order_id", "amount"],
        )

        result = self.validator.validate(
            sql=parsed_sql.original_sql,
            parsed_sql=parsed_sql,
            schema=schema,
            policy_context=policy_context,
        )

        assert result.is_valid is True


class TestSecurityBypassDetection:
    """Test security bypass attempt detection."""

    def test_no_bypass_attempt(self):
        """Test normal query not flagged."""
        sql = "SELECT * FROM orders WHERE region = 'APAC'"
        is_suspicious, techniques = check_sql_security_bypass_attempts(sql)

        assert is_suspicious is False
        assert len(techniques) == 0

    def test_single_comment(self):
        """Test single SQL comment."""
        sql = "SELECT * FROM orders -- comment"
        is_suspicious, techniques = check_sql_security_bypass_attempts(sql)

        assert "sql_comments" in techniques

    def test_block_comment(self):
        """Test block comment."""
        sql = "SELECT * FROM orders /* comment */"
        is_suspicious, techniques = check_sql_security_bypass_attempts(sql)

        assert "sql_comments" in techniques

    def test_union_attack(self):
        """Test UNION attack detection."""
        sql = "SELECT * FROM orders UNION SELECT * FROM passwords"
        is_suspicious, techniques = check_sql_security_bypass_attempts(sql)

        assert "union" in techniques

    def test_hex_encoding(self):
        """Test hex encoding detection."""
        sql = "SELECT * FROM users WHERE id = 0x313131"
        is_suspicious, techniques = check_sql_security_bypass_attempts(sql)

        assert "hex_encoding" in techniques

    def test_string_concatenation(self):
        """Test string concatenation detection."""
        sql = "SELECT * FROM users WHERE name = 'admin' + 'test'"
        is_suspicious, techniques = check_sql_security_bypass_attempts(sql)

        assert "string_concatenation" in techniques

    def test_concat_function(self):
        """Test CONCAT function detection."""
        sql = "SELECT CONCAT(username, password) FROM users"
        is_suspicious, techniques = check_sql_security_bypass_attempts(sql)

        assert "string_concatenation" in techniques

    def test_multiple_bypass_techniques(self):
        """Test multiple bypass techniques flagged."""
        sql = "SELECT * FROM orders -- comment UNION SELECT password FROM users"
        is_suspicious, techniques = check_sql_security_bypass_attempts(sql)

        assert is_suspicious is True
        assert len(techniques) >= 2
