"""Evaluation cases for NL2SQL pipeline.

This module provides 100+ evaluation cases covering:
- Success cases
- Syntax error cases
- Policy violation cases
- Semantic validation cases
- Execution failure cases
- Edge cases
- Security bypass attempts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class CaseCategory(str, Enum):
    """Category of evaluation case."""

    SUCCESS = "success"
    SYNTAX_ERROR = "syntax_error"
    POLICY_VIOLATION = "policy_violation"
    SEMANTIC_ERROR = "semantic_error"
    EXECUTION_ERROR = "execution_error"
    SECURITY_BYPASS = "security_bypass"
    EDGE_CASE = "edge_case"
    COMPLEXITY_EXCEEDED = "complexity_exceeded"


class ExpectedOutcome(str, Enum):
    """Expected outcome of test case."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class EvaluationCase:
    """An evaluation case for NL2SQL testing."""

    case_id: str
    category: CaseCategory
    description: str
    question: str
    domain: str
    expected_outcome: ExpectedOutcome
    expected_sql_pattern: str | None = None
    expected_error: str | None = None
    expected_policy_check: str | None = None
    user_context: dict[str, Any] | None = None
    time_range_start: str | None = None
    time_range_start_end: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "case_id": self.case_id,
            "category": self.category.value,
            "description": self.description,
            "question": self.question,
            "domain": self.domain,
            "expected_outcome": self.expected_outcome.value,
            "expected_sql_pattern": self.expected_sql_pattern,
            "expected_error": self.expected_error,
            "expected_policy_check": self.expected_policy_check,
            "user_context": self.user_context,
            "metadata": self.metadata,
        }


# ============================================================================
# SUCCESS CASES (cases 001-030)
# ============================================================================

SUCCESS_CASES = [
    # Basic aggregation
    EvaluationCase(
        case_id="nl2sql-001",
        category=CaseCategory.SUCCESS,
        description="Simple revenue total by region",
        question="What is the total revenue by region?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="SELECT.*GROUP BY.*region",
    ),
    EvaluationCase(
        case_id="nl2sql-002",
        category=CaseCategory.SUCCESS,
        description="Count of orders by customer",
        question="How many orders does each customer have?",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="SELECT.*COUNT.*GROUP BY.*customer",
    ),
    EvaluationCase(
        case_id="nl2sql-003",
        category=CaseCategory.SUCCESS,
        description="Average order value by product",
        question="What is the average order value for each product?",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="SELECT.*AVG.*GROUP BY.*product",
    ),
    EvaluationCase(
        case_id="nl2sql-004",
        category=CaseCategory.SUCCESS,
        description="Monthly revenue trend",
        question="Show me the revenue trend over the last 12 months",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="SELECT.*SUM.*GROUP BY.*month",
    ),
    EvaluationCase(
        case_id="nl2sql-005",
        category=CaseCategory.SUCCESS,
        description="Top 10 customers by revenue",
        question="Who are the top 10 customers by revenue?",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="ORDER BY.*DESC.*LIMIT",
    ),

    # Time-based queries
    EvaluationCase(
        case_id="nl2sql-006",
        category=CaseCategory.SUCCESS,
        description="Year-to-date revenue",
        question="What is the year-to-date revenue?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="WHERE.*YEAR.*=",
    ),
    EvaluationCase(
        case_id="nl2sql-007",
        category=CaseCategory.SUCCESS,
        description="Quarter-over-quarter growth",
        question="What is the quarter-over-quarter revenue growth?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-008",
        category=CaseCategory.SUCCESS,
        description="Month-over-month comparison",
        question="Compare this month's revenue to last month",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),

    # Filtering
    EvaluationCase(
        case_id="nl2sql-009",
        category=CaseCategory.SUCCESS,
        description="Revenue for specific region",
        question="What is the total revenue for the APAC region?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="WHERE.*region.*=.*APAC",
    ),
    EvaluationCase(
        case_id="nl2sql-010",
        category=CaseCategory.SUCCESS,
        description="Revenue above threshold",
        question="Show me orders with revenue greater than $10,000",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="WHERE.*>.*10000",
    ),

    # Joins
    EvaluationCase(
        case_id="nl2sql-011",
        category=CaseCategory.SUCCESS,
        description="Revenue with customer details",
        question="What is the revenue by customer name?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="JOIN.*customer",
    ),
    EvaluationCase(
        case_id="nl2sql-012",
        category=CaseCategory.SUCCESS,
        description="Orders with product details",
        question="What products are in each order?",
        domain="supply_chain",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="JOIN.*product",
    ),

    # Complex aggregations
    EvaluationCase(
        case_id="nl2sql-013",
        category=CaseCategory.SUCCESS,
        description="Distinct count by dimension",
        question="How many distinct products were sold?",
        domain="supply_chain",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="COUNT.*DISTINCT",
    ),
    EvaluationCase(
        case_id="nl2sql-014",
        category=CaseCategory.SUCCESS,
        description="Min/Max values",
        question="What is the minimum and maximum order value?",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="MIN.*MAX",
    ),

    # Nested queries
    EvaluationCase(
        case_id="nl2sql-015",
        category=CaseCategory.SUCCESS,
        description="Subquery for comparison",
        question="Which customers have above-average revenue?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="WHERE.*>.*AVG",
    ),

    # CTEs
    EvaluationCase(
        case_id="nl2sql-016",
        category=CaseCategory.SUCCESS,
        description="CTE for intermediate calculation",
        question="Calculate revenue share by region",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="WITH.*AS.*SELECT",
    ),

    # Multiple metrics
    EvaluationCase(
        case_id="nl2sql-017",
        category=CaseCategory.SUCCESS,
        description="Multiple metrics in one query",
        question="Show me total revenue, order count, and average order value",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="SUM.*COUNT.*AVG",
    ),

    # Ranking
    EvaluationCase(
        case_id="nl2sql-018",
        category=CaseCategory.SUCCESS,
        description="Top N by metric",
        question="What are the top 5 products by sales?",
        domain="supply_chain",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="ORDER BY.*DESC.*LIMIT.*5",
    ),
    EvaluationCase(
        case_id="nl2sql-019",
        category=CaseCategory.SUCCESS,
        description="Bottom N by metric",
        question="Which regions have the lowest revenue?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="ORDER BY.*ASC.*LIMIT",
    ),

    # Date functions
    EvaluationCase(
        case_id="nl2sql-020",
        category=CaseCategory.SUCCESS,
        description="Date extraction",
        question="How many orders were placed on each day of the week?",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="EXTRACT.*DOW",
    ),

    # Window functions
    EvaluationCase(
        case_id="nl2sql-021",
        category=CaseCategory.SUCCESS,
        description="Running total",
        question="Show running total of revenue by date",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="SUM.*OVER.*ORDER BY",
    ),

    # Multiple groupings
    EvaluationCase(
        case_id="nl2sql-022",
        category=CaseCategory.SUCCESS,
        description="Multi-dimensional grouping",
        question="Show revenue by region and product category",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="GROUP BY.*,.*",
    ),

    # Having clause
    EvaluationCase(
        case_id="nl2sql-023",
        category=CaseCategory.SUCCESS,
        description="Filter on aggregated value",
        question="Which customers have more than 10 orders?",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="HAVING.*COUNT.*>",
    ),

    # UNION
    EvaluationCase(
        case_id="nl2sql-024",
        category=CaseCategory.SUCCESS,
        description="Combine results from multiple sources",
        question="Combine revenue from online and offline channels",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="UNION",
    ),

    # Complex join
    EvaluationCase(
        case_id="nl2sql-025",
        category=CaseCategory.SUCCESS,
        description="Multi-table join",
        question="Show orders with customer name and product details",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="JOIN.*JOIN",
    ),

    # Null handling
    EvaluationCase(
        case_id="nl2sql-026",
        category=CaseCategory.SUCCESS,
        description="Handle null values",
        question="Count orders excluding null customer IDs",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="WHERE.*IS NOT NULL",
    ),

    # Case statements
    EvaluationCase(
        case_id="nl2sql-027",
        category=CaseCategory.SUCCESS,
        description="Conditional logic",
        question="Categorize orders by size (small/medium/large)",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="CASE.*WHEN.*THEN",
    ),

    # Cross-domain
    EvaluationCase(
        case_id="nl2sql-028",
        category=CaseCategory.SUCCESS,
        description="Finance metrics with supply chain context",
        question="What is the revenue per product shipped?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),

    # Pagination
    EvaluationCase(
        case_id="nl2sql-029",
        category=CaseCategory.SUCCESS,
        description="Paginated results",
        question="Show me the 3rd page of customers (page size 20)",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="LIMIT.*OFFSET",
    ),

    # Complex filter
    EvaluationCase(
        case_id="nl2sql-030",
        category=CaseCategory.SUCCESS,
        description="Complex WHERE clause",
        question="Show high-value orders from premium customers in Q1",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        expected_sql_pattern="WHERE.*AND.*AND",
    ),
]


# ============================================================================
# SYNTAX ERROR CASES (cases 031-045)
# ============================================================================

SYNTAX_ERROR_CASES = [
    EvaluationCase(
        case_id="nl2sql-031",
        category=CaseCategory.SYNTAX_ERROR,
        description="Missing SELECT keyword",
        question="Invalid query - missing SELECT",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
        metadata={"invalid_sql": "SELECT * FROM orders WHERE region = 'APAC' GROUP BY region"},
    ),
    EvaluationCase(
        case_id="nl2sql-032",
        category=CaseCategory.SYNTAX_ERROR,
        description="Unbalanced parentheses",
        question="Invalid query - unbalanced parens",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-033",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid column alias",
        question="Invalid query - missing AS",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-034",
        category=CaseCategory.SYNTAX_ERROR,
        description="Missing FROM clause",
        question="Invalid query - no FROM",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-035",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid GROUP BY expression",
        question="Invalid query - GROUP BY not in SELECT",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-036",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid JOIN syntax",
        question="Invalid query - malformed JOIN",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-037",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid date literal",
        question="Invalid query - bad date format",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-038",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid string literal",
        question="Invalid query - unclosed string",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-039",
        category=CaseCategory.SYNTAX_ERROR,
        description="Multiple statements",
        question="Invalid query - multiple statements",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
        metadata={"invalid_sql": "SELECT * FROM orders; SELECT * FROM customers"},
    ),
    EvaluationCase(
        case_id="nl2sql-040",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid aggregate function",
        question="Invalid query - wrong aggregate",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-041",
        category=CaseCategory.SYNTAX_ERROR,
        description="Missing GROUP BY with aggregate",
        question="Invalid query - no GROUP BY",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-042",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid ORDER BY position",
        question="Invalid query - ORDER BY before WHERE",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-043",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid LIMIT value",
        question="Invalid query - negative LIMIT",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-044",
        category=CaseCategory.SYNTAX_ERROR,
        description="Invalid column reference",
        question="Invalid query - column not in scope",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-045",
        category=CaseCategory.SYNTAX_ERROR,
        description="Duplicate column alias",
        question="Invalid query - duplicate aliases",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
]


# ============================================================================
# POLICY VIOLATION CASES (cases 046-060)
# ============================================================================

POLICY_VIOLATION_CASES = [
    EvaluationCase(
        case_id="nl2sql-046",
        category=CaseCategory.POLICY_VIOLATION,
        description="Attempt to access admin table",
        question="Show me all data from admin_users",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="PERMISSION_DENIED",
        expected_policy_check="table_access",
    ),
    EvaluationCase(
        case_id="nl2sql-047",
        category=CaseCategory.POLICY_VIOLATION,
        description="Query without permission",
        question="Show me the password_hash column",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="sensitive_columns",
        user_context={"roles": ["viewer"]},
    ),
    EvaluationCase(
        case_id="nl2sql-048",
        category=CaseCategory.POLICY_VIOLATION,
        description="Access to denied table",
        question="Show me data from audit_log",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="PERMISSION_DENIED",
        expected_policy_check="table_access",
        user_context={"roles": ["viewer"], "denied_tables": ["audit_log"]},
    ),
    EvaluationCase(
        case_id="nl2sql-049",
        category=CaseCategory.POLICY_VIOLATION,
        description="Sensitive column access denied",
        question="Show me credit card numbers",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="sensitive_columns",
        user_context={"roles": ["analyst"]},
    ),
    EvaluationCase(
        case_id="nl2sql-050",
        category=CaseCategory.POLICY_VIOLATION,
        description="Region restriction violated",
        question="Show me data from all regions",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="PERMISSION_DENIED",
        expected_policy_check="region_restriction",
        user_context={"roles": ["regional_user"], "allowed_regions": ["APAC"]},
    ),
    EvaluationCase(
        case_id="nl2sql-051",
        category=CaseCategory.POLICY_VIOLATION,
        description="Tenant isolation violated",
        question="Show me data from tenant X",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="PERMISSION_DENIED",
        expected_policy_check="tenant_restriction",
        user_context={"roles": ["tenant_user"], "tenant_id": "tenant_123"},
    ),
    EvaluationCase(
        case_id="nl2sql-052",
        category=CaseCategory.POLICY_VIOLATION,
        description="Metric permission denied",
        question="Calculate profit margin",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="PERMISSION_DENIED",
        expected_policy_check="metric_permission",
        user_context={"roles": ["basic_viewer"], "metric_permissions": []},
    ),
    EvaluationCase(
        case_id="nl2sql-053",
        category=CaseCategory.POLICY_VIOLATION,
        description="Cross-domain access denied",
        question="Join finance and HR data",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="POLICY_VIOLATION",
        expected_policy_check="cross_domain",
    ),
    EvaluationCase(
        case_id="nl2sql-054",
        category=CaseCategory.POLICY_VIOLATION,
        description="Query too complex",
        question="Show me all combinations of all dimensions",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="COMPLEXITY_EXCEEDED",
        expected_policy_check="complexity",
    ),
    EvaluationCase(
        case_id="nl2sql-055",
        category=CaseCategory.POLICY_VIOLATION,
        description="Missing LIMIT on large table",
        question="Show all orders",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_policy_check="row_limit",
    ),
    EvaluationCase(
        case_id="nl2sql-056",
        category=CaseCategory.POLICY_VIOLATION,
        description="Unauthorized dimension access",
        question="Break down by employee_id",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="PERMISSION_DENIED",
        expected_policy_check="dimension_permission",
    ),
    EvaluationCase(
        case_id="nl2sql-057",
        category=CaseCategory.POLICY_VIOLATION,
        description="API key column access",
        question="Show me all API keys",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="sensitive_columns",
    ),
    EvaluationCase(
        case_id="nl2sql-058",
        category=CaseCategory.POLICY_VIOLATION,
        description="SSN column access",
        question="Show me employee SSNs",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="sensitive_columns",
    ),
    EvaluationCase(
        case_id="nl2sql-059",
        category=CaseCategory.POLICY_VIOLATION,
        description="Invalid join path",
        question="Join orders directly to products",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="INVALID_JOIN",
        expected_policy_check="valid_joins",
    ),
    EvaluationCase(
        case_id="nl2sql-060",
        category=CaseCategory.POLICY_VIOLATION,
        description="Multiple violations",
        question="Show all columns from all tables including passwords",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="multiple_violations",
    ),
]


# ============================================================================
# SEMANTIC ERROR CASES (cases 061-075)
# ============================================================================

SEMANTIC_ERROR_CASES = [
    EvaluationCase(
        case_id="nl2sql-061",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Invalid metric formula",
        question="Sum of revenue should not use COUNT",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="AGGREGATION_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-062",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Unsupported time grain",
        question="Show revenue by second",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="GRAIN_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-063",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Incompatible dimension",
        question="Break down revenue by supplier_id",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="SEMANTIC_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-064",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Derived metric misuse",
        question="Sum profit_margin directly",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="INVALID_METRIC_FORMULA",
    ),
    EvaluationCase(
        case_id="nl2sql-065",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Missing required filter",
        question="Show revenue without date filter",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="SEMANTIC_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-066",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Invalid join cardinality",
        question="One-to-many join misused",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="SEMANTIC_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-067",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Time range outside availability",
        question="Show revenue for year 1990",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="EMPTY_UNEXPECTED_RESULT",
    ),
    EvaluationCase(
        case_id="nl2sql-068",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Conflicting metrics",
        question="Sum revenue and profit_margin together",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="SEMANTIC_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-069",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Metric version mismatch",
        question="Use old revenue definition",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="SEMANTIC_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-070",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Dimension not in metric scope",
        question="Break down product_revenue by employee",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="SEMANTIC_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-071",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Aggregation on non-aggregatable metric",
        question="Sum customer_id",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="AGGREGATION_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-072",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Grain not supported by metric",
        question="Show weekly profit",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="GRAIN_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-073",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Missing required join",
        question="Show order revenue without customer join",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="SEMANTIC_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-074",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Metric formula not respected",
        question="Calculate margin as sum of (revenue - cost)",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="INVALID_METRIC_FORMULA",
    ),
    EvaluationCase(
        case_id="nl2sql-075",
        category=CaseCategory.SEMANTIC_ERROR,
        description="Incompatible time grain",
        question="Show monthly revenue trend with daily granularity",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="GRAIN_ERROR",
    ),
]


# ============================================================================
# EXECUTION ERROR CASES (cases 076-085)
# ============================================================================

EXECUTION_ERROR_CASES = [
    EvaluationCase(
        case_id="nl2sql-076",
        category=CaseCategory.EXECUTION_ERROR,
        description="Query timeout",
        question="Show all possible combinations",
        domain="finance",
        expected_outcome=ExpectedOutcome.TIMEOUT,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-077",
        category=CaseCategory.EXECUTION_ERROR,
        description="Table does not exist",
        question="Query non_existent_table",
        domain="finance",
        expected_outcome=ExpectedOutcome.ERROR,
        expected_error="UNKNOWN_TABLE",
    ),
    EvaluationCase(
        case_id="nl2sql-078",
        category=CaseCategory.EXECUTION_ERROR,
        description="Column does not exist",
        question="Select non_existent_column",
        domain="finance",
        expected_outcome=ExpectedOutcome.ERROR,
        expected_error="UNKNOWN_COLUMN",
    ),
    EvaluationCase(
        case_id="nl2sql-079",
        category=CaseCategory.EXECUTION_ERROR,
        description="Division by zero",
        question="Calculate revenue per order where orders can be zero",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="EXECUTION_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-080",
        category=CaseCategory.EXECUTION_ERROR,
        description="Type mismatch in comparison",
        question="Compare revenue string to number",
        domain="finance",
        expected_outcome=ExpectedOutcome.ERROR,
        expected_error="TYPE_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-081",
        category=CaseCategory.EXECUTION_ERROR,
        description="Invalid date operation",
        question="Add string to date",
        domain="finance",
        expected_outcome=ExpectedOutcome.ERROR,
        expected_error="TYPE_MISMATCH",
    ),
    EvaluationCase(
        case_id="nl2sql-082",
        category=CaseCategory.EXECUTION_ERROR,
        description="Connection failure",
        question="Any query when DB is down",
        domain="finance",
        expected_outcome=ExpectedOutcome.ERROR,
        expected_error="CONNECTION_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-083",
        category=CaseCategory.EXECUTION_ERROR,
        description="Memory exceeded",
        question="Generate huge cartesian product",
        domain="finance",
        expected_outcome=ExpectedOutcome.ERROR,
        expected_error="RESOURCE_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-084",
        category=CaseCategory.EXECUTION_ERROR,
        description="Null pointer in aggregation",
        question="Sum column with all nulls",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="NULL_VALUE",
    ),
    EvaluationCase(
        case_id="nl2sql-085",
        category=CaseCategory.EXECUTION_ERROR,
        description="Arithmetic overflow",
        question="Sum extremely large numbers",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="OVERFLOW",
    ),
]


# ============================================================================
# SECURITY BYPASS ATTEMPTS (cases 086-095)
# ============================================================================

SECURITY_BYPASS_CASES = [
    EvaluationCase(
        case_id="nl2sql-086",
        category=CaseCategory.SECURITY_BYPASS,
        description="SQL comment injection",
        question="Show all -- data",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="sql_injection",
    ),
    EvaluationCase(
        case_id="nl2sql-087",
        category=CaseCategory.SECURITY_BYPASS,
        description="UNION injection",
        question="Get revenue UNION ALL SELECT password FROM admin",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="union_bypass",
    ),
    EvaluationCase(
        case_id="nl2sql-088",
        category=CaseCategory.SECURITY_BYPASS,
        description="Hex encoding bypass",
        question="Query with 0xencoded payload",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="encoding_bypass",
    ),
    EvaluationCase(
        case_id="nl2sql-089",
        category=CaseCategory.SECURITY_BYPASS,
        description="String concatenation",
        question="Query with CONCAT for injection",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="concatenation_bypass",
    ),
    EvaluationCase(
        case_id="nl2sql-090",
        category=CaseCategory.SECURITY_BYPASS,
        description="Nested subquery injection",
        question="Query with nested (SELECT)",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="SECURITY_POLICY",
        expected_policy_check="nested_subquery",
    ),
    EvaluationCase(
        case_id="nl2sql-091",
        category=CaseCategory.SECURITY_BYPASS,
        description="Multi-statement injection",
        question="Query; DROP TABLE orders",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="multi_statement",
    ),
    EvaluationCase(
        case_id="nl2sql-092",
        category=CaseCategory.SECURITY_BYPASS,
        description="Block comment injection",
        question="Query /* comment */ bypass",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="comment_injection",
    ),
    EvaluationCase(
        case_id="nl2sql-093",
        category=CaseCategory.SECURITY_BYPASS,
        description="OR 1=1 injection",
        question="WHERE region = 'APAC' OR 1=1",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="or_injection",
    ),
    EvaluationCase(
        case_id="nl2sql-094",
        category=CaseCategory.SECURITY_BYPASS,
        description="Empty password bypass",
        question="Login with '' OR ''='",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="empty_injection",
    ),
    EvaluationCase(
        case_id="nl2sql-095",
        category=CaseCategory.SECURITY_BYPASS,
        description="CTE for bypass",
        question="WITH admin AS (SELECT * FROM passwords) SELECT * FROM admin",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SECURITY_POLICY",
        expected_policy_check="cte_bypass",
    ),
]


# ============================================================================
# EDGE CASES (cases 096-110)
# ============================================================================

EDGE_CASES = [
    EvaluationCase(
        case_id="nl2sql-096",
        category=CaseCategory.EDGE_CASE,
        description="Empty result is expected",
        question="Show orders from Antarctica",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.SUCCESS,
        user_context={"allow_empty_results": True},
    ),
    EvaluationCase(
        case_id="nl2sql-097",
        category=CaseCategory.EDGE_CASE,
        description="Single row result",
        question="What is the total company revenue?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-098",
        category=CaseCategory.EDGE_CASE,
        description="All NULLs in result",
        question="Sum a column with all NULLs",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-099",
        category=CaseCategory.EDGE_CASE,
        description="Duplicate rows",
        question="Select without DISTINCT",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
    ),
    EvaluationCase(
        case_id="nl2sql-100",
        category=CaseCategory.EDGE_CASE,
        description="Very long string values",
        question="Select description column with TEXT data",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-101",
        category=CaseCategory.EDGE_CASE,
        description="Special characters in filter",
        question="Search for product with apostrophe in name",
        domain="supply_chain",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-102",
        category=CaseCategory.EDGE_CASE,
        description="Unicode in question",
        question="Show 日本語 データ",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-103",
        category=CaseCategory.EDGE_CASE,
        description="Extremely long question",
        question="What is the total revenue for the APAC region for the year 2024, broken down by product category, including only orders with value greater than 1000, sorted by revenue descending, limited to top 100?",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-104",
        category=CaseCategory.EDGE_CASE,
        description="Ambiguous question",
        question="Show revenue",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_policy_check="ambiguous_query",
    ),
    EvaluationCase(
        case_id="nl2sql-105",
        category=CaseCategory.EDGE_CASE,
        description="Self-join edge case",
        question="Compare each customer's revenue to average",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-106",
        category=CaseCategory.EDGE_CASE,
        description="Division by zero in calculation",
        question="Calculate revenue per order when some orders have zero quantity",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
    ),
    EvaluationCase(
        case_id="nl2sql-107",
        category=CaseCategory.EDGE_CASE,
        description="Timezone edge case",
        question="Show revenue by day in UTC",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-108",
        category=CaseCategory.EDGE_CASE,
        description="Leading zeros in numeric strings",
        question="Select zip codes starting with 0",
        domain="finance",
        expected_outcome=ExpectedOutcome.SUCCESS,
    ),
    EvaluationCase(
        case_id="nl2sql-109",
        category=CaseCategory.EDGE_CASE,
        description="Negative LIMIT",
        question="Show top -5 orders",
        domain="sales_operations",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="SYNTAX_ERROR",
    ),
    EvaluationCase(
        case_id="nl2sql-110",
        category=CaseCategory.EDGE_CASE,
        description="NULL in IN clause",
        question="Filter by list containing NULL",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
    ),
]


# ============================================================================
# COMPLEXITY EXCEEDED CASES (cases 111-120)
# ============================================================================

COMPLEXITY_CASES = [
    EvaluationCase(
        case_id="nl2sql-111",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Too many tables",
        question="Join 15 tables",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-112",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Deep nesting",
        question="5 levels of subqueries",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-113",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Too many CTEs",
        question="10+ CTEs",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-114",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Massive cartesian product",
        question="Join large tables without filters",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-115",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Too many aggregations",
        question="Count distinct on high-cardinality columns",
        domain="finance",
        expected_outcome=ExpectedOutcome.TIMEOUT,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-116",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Large IN clause",
        question="Filter with 10000 values",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-117",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="OR chain explosion",
        question="Long chain of OR conditions",
        domain="finance",
        expected_outcome=ExpectedOutcome.WARNING,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-118",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Recursive CTE without limit",
        question="Recursive CTE",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-119",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Pattern matching on large text",
        question="LIKE '%' on millions of rows",
        domain="finance",
        expected_outcome=ExpectedOutcome.TIMEOUT,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
    EvaluationCase(
        case_id="nl2sql-120",
        category=CaseCategory.COMPLEXITY_EXCEEDED,
        description="Cross join without limit",
        question="Cross join two large tables",
        domain="finance",
        expected_outcome=ExpectedOutcome.REJECTED,
        expected_error="COMPLEXITY_EXCEEDED",
    ),
]


# ============================================================================
# ALL CASES
# ============================================================================

ALL_EVALUATION_CASES = (
    SUCCESS_CASES +
    SYNTAX_ERROR_CASES +
    POLICY_VIOLATION_CASES +
    SEMANTIC_ERROR_CASES +
    EXECUTION_ERROR_CASES +
    SECURITY_BYPASS_CASES +
    EDGE_CASES +
    COMPLEXITY_CASES
)


def get_cases_by_category(category: CaseCategory) -> list[EvaluationCase]:
    """Get all cases in a category.

    Args:
        category: Category to filter by

    Returns:
        List of cases in category
    """
    return [c for c in ALL_EVALUATION_CASES if c.category == category]


def get_case_by_id(case_id: str) -> EvaluationCase | None:
    """Get a case by ID.

    Args:
        case_id: Case ID

    Returns:
        Case or None
    """
    for case in ALL_EVALUATION_CASES:
        if case.case_id == case_id:
            return case
    return None


def get_cases_by_domain(domain: str) -> list[EvaluationCase]:
    """Get all cases for a domain.

    Args:
        domain: Domain name

    Returns:
        List of cases for domain
    """
    return [c for c in ALL_EVALUATION_CASES if c.domain == domain]


def get_cases_by_outcome(outcome: ExpectedOutcome) -> list[EvaluationCase]:
    """Get all cases with expected outcome.

    Args:
        outcome: Expected outcome

    Returns:
        List of cases with outcome
    """
    return [c for c in ALL_EVALUATION_CASES if c.expected_outcome == outcome]


def get_case_count() -> int:
    """Get total number of evaluation cases.

    Returns:
        Total count
    """
    return len(ALL_EVALUATION_CASES)


def get_case_summary() -> dict[str, int]:
    """Get summary of cases by category.

    Returns:
        Category -> count mapping
    """
    summary: dict[str, int] = {}
    for case in ALL_EVALUATION_CASES:
        category = case.category.value
        summary[category] = summary.get(category, 0) + 1
    return summary
