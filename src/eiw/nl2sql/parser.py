"""SQL Parser and AST Validation using SQLGlot.

This module provides:
- SQLGlot AST parsing
- Syntax validation
- AST analysis
- Security validation
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


logger = get_structured_logger(__name__, "sql_parser")


@dataclass
class ParsedSQL:
    """Parsed SQL with AST analysis."""

    original_sql: str
    parsed: Any  # sqlglot.ast.Node
    tables: list[str]
    columns: list[str]
    joins: list[str]
    subqueries: list[str]
    ctes: list[str]
    functions: list[str]
    has_union: bool
    has_group_by: bool
    has_order_by: bool
    has_limit: bool
    statement_count: int


class SQLParser:
    """SQL Parser using SQLGlot for AST validation.

    This parser:
    1. Parses SQL using SQLGlot
    2. Validates syntax
    3. Extracts AST metadata
    4. Checks for dangerous operations
    """

    # Operations that are explicitly forbidden
    FORBIDDEN_OPERATIONS = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "CREATE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "COPY",
        "ATTACH",
        "REPLACE",
    }

    # Keywords that might indicate dangerous operations
    DANGEROUS_KEYWORDS = {
        "PRAGMA",
        "EXEC",
        "EXECUTE",
        "CALL",
        "LOAD",
        "EXPORT",
    }

    def __init__(self) -> None:
        """Initialize SQL parser."""
        self._sqlglot = None  # Lazy import

    def _get_sqlglot(self) -> Any:
        """Get or import sqlglot module.

        Returns:
            sqlglot module
        """
        if self._sqlglot is None:
            try:
                import sqlglot
                self._sqlglot = sqlglot
            except ImportError:
                logger.warning("SQLGlot not installed, using basic validation")
                return None
        return self._sqlglot

    def parse(self, sql: str) -> ParsedSQL | None:
        """Parse SQL and extract AST metadata.

        Args:
            sql: SQL to parse

        Returns:
            Parsed SQL with metadata, or None if parsing fails
        """
        with trace_span("nl2sql.parse", {"sql_length": len(sql)}):
            sqlglot = self._get_sqlglot()

            if sqlglot is None:
                return self._basic_parse(sql)

            try:
                # Parse SQL
                statements = sqlglot.parse(sql)

                if not statements:
                    return None

                # Extract metadata from first statement
                stmt = statements[0]

                # Extract tables, columns, joins
                tables = self._extract_tables(stmt)
                columns = self._extract_columns(stmt)
                joins = self._extract_joins(stmt)
                subqueries = self._extract_subqueries(stmt)
                ctes = self._extract_ctes(stmt)
                functions = self._extract_functions(stmt)

                # Check for specific clauses
                exp = sqlglot.exp
                has_union = any(
                    isinstance(node, exp.Union)
                    for node in stmt.walk()
                )
                has_group_by = stmt.find(exp.Group) is not None
                has_order_by = stmt.find(exp.Order) is not None
                has_limit = stmt.find(exp.Limit) is not None

                return ParsedSQL(
                    original_sql=sql,
                    parsed=stmt,
                    tables=tables,
                    columns=columns,
                    joins=joins,
                    subqueries=subqueries,
                    ctes=ctes,
                    functions=functions,
                    has_union=has_union,
                    has_group_by=has_group_by,
                    has_order_by=has_order_by,
                    has_limit=has_limit,
                    statement_count=len(statements),
                )

            except Exception as e:
                logger.warning(f"SQL parse failed: {e}")
                return None

    def _basic_parse(self, sql: str) -> ParsedSQL | None:
        """Basic parse without SQLGlot.

        Args:
            sql: SQL to parse

        Returns:
            Basic parsed SQL
        """
        import re

        # Extract tables (simplified)
        tables = []
        from_match = re.search(r"FROM\s+([^\s,]+)", sql, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1))

        # Extract columns
        columns = []
        select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_cols = select_match.group(1)
            # Extract column names (simplified)
            for col in re.findall(r"(\w+(?:\.\w+)?)\s*(?:AS|,|\s+FROM|\s+WHERE)", select_cols, re.IGNORECASE):
                if col.upper() not in ("SELECT", ""):
                    columns.append(col)

        return ParsedSQL(
            original_sql=sql,
            parsed=None,
            tables=tables,
            columns=columns,
            joins=[],
            subqueries=[],
            ctes=[],
            functions=[],
            has_union="UNION" in sql.upper(),
            has_group_by="GROUP BY" in sql.upper(),
            has_order_by="ORDER BY" in sql.upper(),
            has_limit="LIMIT" in sql.upper(),
            statement_count=1,
        )

    def validate(
        self,
        sql: str,
        allowed_tables: list[str] | None = None,
        allowed_columns: list[str] | None = None,
        max_complexity: int = 10,
    ) -> SQLValidationResult:
        """Validate SQL for correctness and security.

        Args:
            sql: SQL to validate
            allowed_tables: List of allowed table names
            allowed_columns: List of allowed column names
            max_complexity: Maximum query complexity

        Returns:
            Validation result
        """
        with trace_span("nl2sql.parse_validate", {
            "sql_length": len(sql),
            "allowed_tables_count": len(allowed_tables or []),
        }):
            errors: list[SQLValidationErrorCategory] = []
            warnings: list[str] = []
            details_parts: list[str] = []

            # Check for multiple statements
            parsed = self.parse(sql)

            if parsed is None:
                errors.append(SQLValidationErrorCategory.SYNTAX_ERROR)
                return SQLValidationResult(
                    is_valid=False,
                    status=ExecutionStatus.REJECTED,
                    errors=errors,
                    warnings=warnings,
                    details="SQL syntax is invalid",
                )

            if parsed.statement_count > 1:
                errors.append(SQLValidationErrorCategory.SYNTAX_ERROR)
                details_parts.append(f"Multiple statements detected: {parsed.statement_count}")

            # Check statement type
            stmt_type = self._check_statement_type(parsed)
            if stmt_type == "forbidden":
                errors.append(SQLValidationErrorCategory.SECURITY_POLICY)
                details_parts.append("SQL contains forbidden statement type")
            elif stmt_type == "unknown":
                errors.append(SQLValidationErrorCategory.SYNTAX_ERROR)
                details_parts.append("SQL statement type not recognized")

            # Check for dangerous keywords
            dangerous = self._check_dangerous_keywords(sql)
            if dangerous:
                errors.append(SQLValidationErrorCategory.SECURITY_POLICY)
                details_parts.append(f"Dangerous keywords found: {dangerous}")

            # Check tables
            if allowed_tables:
                invalid_tables = [
                    t for t in parsed.tables
                    if t not in allowed_tables
                ]
                if invalid_tables:
                    errors.append(SQLValidationErrorCategory.UNKNOWN_TABLE)
                    details_parts.append(f"Unknown tables: {invalid_tables}")

            # Check complexity
            complexity = self._calculate_complexity(parsed)
            if complexity > max_complexity:
                errors.append(SQLValidationErrorCategory.COMPLEXITY_EXCEEDED)
                warnings.append(f"Query complexity ({complexity}) exceeds limit ({max_complexity})")

            # Check for UNION bypass
            if parsed.has_union:
                warnings.append("Query contains UNION - verify all parts are valid")

            # Check for subqueries
            if parsed.subqueries:
                warnings.append(f"Query contains {len(parsed.subqueries)} subqueries")

            # Check for CTEs
            if parsed.ctes:
                warnings.append(f"Query contains {len(parsed.ctes)} CTEs")

            is_valid = len(errors) == 0

            return SQLValidationResult(
                is_valid=is_valid,
                status=ExecutionStatus.VALID if is_valid else ExecutionStatus.REJECTED,
                errors=errors,
                warnings=warnings,
                details="; ".join(details_parts) if details_parts else "Validation passed",
            )

    def _check_statement_type(self, parsed: ParsedSQL) -> str:
        """Check the type of SQL statement.

        Args:
            parsed: Parsed SQL

        Returns:
            Statement type: "select", "forbidden", or "unknown"
        """
        if parsed.parsed is None:
            # Basic check without AST
            sql_upper = parsed.original_sql.strip().upper()
            if sql_upper.startswith("SELECT"):
                return "select"
            elif any(sql_upper.startswith(op) for op in self.FORBIDDEN_OPERATIONS):
                return "forbidden"
            else:
                return "unknown"

        # Use SQLGlot AST
        import sqlglot.expressions as exp

        if isinstance(parsed.parsed, (exp.Select, exp.Subquery)):
            return "select"
        elif isinstance(parsed.parsed, (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Alter,
            exp.Create,
            exp.TruncateTable,
        )):
            return "forbidden"
        else:
            return "unknown"

    def _check_dangerous_keywords(self, sql: str) -> list[str]:
        """Check for dangerous keywords.

        Args:
            sql: SQL to check

        Returns:
            List of dangerous keywords found
        """
        sql_upper = sql.upper()
        found = []

        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in sql_upper:
                # Check it's not in a string literal
                found.append(keyword)

        return found

    def _calculate_complexity(self, parsed: ParsedSQL) -> int:
        """Calculate query complexity.

        Args:
            parsed: Parsed SQL

        Returns:
            Complexity score
        """
        complexity = 0

        # Tables
        complexity += len(parsed.tables)

        # Joins
        complexity += len(parsed.joins) * 2

        # Subqueries
        complexity += len(parsed.subqueries)

        # CTEs
        complexity += len(parsed.ctes)

        # UNION
        if parsed.has_union:
            complexity += 2

        # Functions
        complexity += len(parsed.functions) // 2

        return complexity

    def _extract_tables(self, stmt: Any) -> list[str]:
        """Extract table names from AST.

        Args:
            stmt: SQLGlot statement

        Returns:
            List of table names
        """
        import sqlglot.expressions as exp

        tables = []
        for node in stmt.walk():
            if isinstance(node, exp.Table):
                if node.name and node.name not in tables:
                    tables.append(node.name)

        return tables

    def _extract_columns(self, stmt: Any) -> list[str]:
        """Extract column names from AST.

        Args:
            stmt: SQLGlot statement

        Returns:
            List of column names
        """
        import sqlglot.expressions as exp

        columns = []
        for node in stmt.walk():
            if isinstance(node, exp.Column):
                col_name = node.name
                if col_name and col_name not in columns:
                    columns.append(col_name)

        return columns

    def _extract_joins(self, stmt: Any) -> list[str]:
        """Extract join information from AST.

        Args:
            stmt: SQLGlot statement

        Returns:
            List of join descriptions
        """
        import sqlglot.expressions as exp

        joins = []
        for node in stmt.walk():
            if isinstance(node, exp.Join):
                if node.find(exp.Table):
                    joins.append(str(node))

        return joins

    def _extract_subqueries(self, stmt: Any) -> list[str]:
        """Extract subquery information from AST.

        Args:
            stmt: SQLGlot statement

        Returns:
            List of subquery descriptions
        """
        import sqlglot.expressions as exp

        subqueries = []
        for node in stmt.walk():
            if isinstance(node, exp.Subquery):
                subqueries.append(str(node)[:100])

        return subqueries

    def _extract_ctes(self, stmt: Any) -> list[str]:
        """Extract CTE names from AST.

        Args:
            stmt: SQLGlot statement

        Returns:
            List of CTE names
        """
        import sqlglot.expressions as exp

        ctes = []
        for node in stmt.walk():
            if isinstance(node, exp.CTE):
                if node.alias:
                    ctes.append(node.alias)

        return ctes

    def _extract_functions(self, stmt: Any) -> list[str]:
        """Extract function names from AST.

        Args:
            stmt: SQLGlot statement

        Returns:
            List of function names
        """
        import sqlglot.expressions as exp

        functions = []
        for node in stmt.walk():
            if isinstance(node, exp.Func):
                functions.append(type(node).__name__)

        return list(set(functions))
