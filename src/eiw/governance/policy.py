"""Policy Engine for Enterprise Data Agent.

Implements access control and data governance policies:
- Metric and dimension access control
- Row-level security
- Data classification enforcement
- Query policy validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class DataClassification(Enum):
    """Data classification levels."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


@dataclass
class AccessPolicy:
    """Access policy definition."""

    policy_id: str
    policy_version: str
    effective_date: date
    rules: list[PolicyRule] = field(default_factory=list)


@dataclass
class PolicyRule:
    """A single policy rule."""

    rule_id: str
    resource_type: str  # metric, dimension, table, column
    resource_id: str
    action: str  # read, write, execute
    principals: list[str]  # roles, users
    conditions: dict[str, Any] = field(default_factory=dict)
    deny: bool = False  # True = explicit deny, False = allow


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""

    allowed: bool
    reason: str
    applied_rules: list[str] = field(default_factory=list)
    masked_fields: list[str] = field(default_factory=list)
    row_filters: list[str] = field(default_factory=list)


@dataclass
class UserPolicyContext:
    """User context for policy evaluation."""

    user_id: str
    tenant_id: str
    roles: list[str]
    allowed_metric_ids: list[str] = field(default_factory=list)
    allowed_dimension_ids: list[str] = field(default_factory=list)
    denied_metric_ids: list[str] = field(default_factory=list)
    data_classification_ceiling: DataClassification = DataClassification.INTERNAL
    row_filters: dict[str, str] = field(default_factory=dict)  # table -> filter expression
    column_masks: dict[str, list[str]] = field(default_factory=dict)  # table -> masked columns


class PolicyEngine:
    """Evaluates access policies and enforces governance rules.

    This engine implements:
    1. Metric/dimension access control
    2. Row-level security (RLS)
    3. Column-level masking
    4. Data classification enforcement
    5. Audit logging
    """

    # Predefined policies for enterprise scenarios
    ROLE_POLICIES: dict[str, list[PolicyRule]] = {
        "CFO": [
            PolicyRule("r1", "metric", "*", "read", ["CFO"], deny=False),
            PolicyRule("r2", "dimension", "*", "read", ["CFO"], deny=False),
            PolicyRule("r3", "table", "employee_salary", "read", ["CFO"], deny=False),
            PolicyRule("r4", "column", "customer_pii", "read", ["CFO"], deny=True),
        ],
        "Finance Analyst": [
            PolicyRule("r5", "metric", "revenue,gross_profit,net_income", "read", ["Finance Analyst"], deny=False),
            PolicyRule("r6", "metric", "executive_compensation,merger_details", "read", ["Finance Analyst"], deny=True),
            PolicyRule("r7", "dimension", "*", "read", ["Finance Analyst"], deny=False),
        ],
        "Regional Manager": [
            PolicyRule("r8", "metric", "sales,orders,customers", "read", ["Regional Manager"], deny=False),
            PolicyRule("r9", "metric", "cost,profit,payroll", "read", ["Regional Manager"], deny=True),
            PolicyRule("r10", "table", "regional_sales", "read", ["Regional Manager"], deny=False),
            PolicyRule("r11", "row", "*", "read", ["Regional Manager"], conditions={"region_match": True}),
        ],
        "Sales Manager": [
            PolicyRule("r12", "metric", "sales,orders,conversions", "read", ["Sales Manager"], deny=False),
            PolicyRule("r13", "dimension", "region", "read", ["Sales Manager"], deny=False),
            PolicyRule("r14", "table", "customer_pii", "read", ["Sales Manager"], deny=True),
        ],
    }

    # Dangerous SQL patterns to block
    SQL_DANGEROUS_PATTERNS = [
        r"(?i)\bDROP\b",
        r"(?i)\bDELETE\b",
        r"(?i)\bUPDATE\b",
        r"(?i)\bINSERT\b",
        r"(?i)\bTRUNCATE\b",
        r"(?i)\bALTER\b",
        r"(?i)\bCREATE\s+(TABLE|DATABASE|SCHEMA)\b",
        r"(?i)--.*\bPASSWORD\b",
        r"(?i);\s*\bDROP\b",
        r"(?i)\bUNION\s+SELECT\b.*\bFROM\b",
    ]

    def __init__(self) -> None:
        """Initialize policy engine."""
        self._policies: dict[str, AccessPolicy] = {}
        self._audit_log: list[dict[str, Any]] = []

    def check_metric_access(
        self,
        user_context: dict[str, Any],
        metric_ids: list[str],
    ) -> list[str]:
        """Check if user has access to requested metrics.

        Args:
            user_context: User context
            metric_ids: Requested metric IDs

        Returns:
            List of denied metric IDs (empty = all allowed)
        """
        denied: list[str] = []

        # Get user's allowed metrics
        allowed_metrics = set(user_context.get("allowed_metric_ids", ["*"]))
        denied_metrics = set(user_context.get("denied_metric_ids", []))

        for metric_id in metric_ids:
            # Check explicit deny
            if metric_id in denied_metrics:
                denied.append(metric_id)
                continue

            # Check allowed list
            if "*" not in allowed_metrics and metric_id not in allowed_metrics:
                denied.append(metric_id)

        return denied

    def check_dimension_access(
        self,
        user_context: dict[str, Any],
        dimension_ids: list[str],
    ) -> list[str]:
        """Check if user has access to requested dimensions."""
        denied: list[str] = []

        allowed_dimensions = set(user_context.get("allowed_dimension_ids", ["*"]))
        denied_dimensions = set(user_context.get("denied_dimension_ids", []))

        for dim_id in dimension_ids:
            if dim_id in denied_dimensions:
                denied.append(dim_id)
                continue

            if "*" not in allowed_dimensions and dim_id not in allowed_dimensions:
                denied.append(dim_id)

        return denied

    def evaluate_table_access(
        self,
        user_context: dict[str, Any],
        table_name: str,
        action: str = "read",
    ) -> PolicyDecision:
        """Evaluate access to a table.

        Args:
            user_context: User context
            table_name: Table to access
            action: Action (read, write)

        Returns:
            Policy decision
        """
        roles = user_context.get("roles", [])
        applied_rules: list[str] = []

        # Check role-based policies
        for role in roles:
            if role in self.ROLE_POLICIES:
                for rule in self.ROLE_POLICIES[role]:
                    if rule.resource_type == "table" and self._matches_resource(rule.resource_id, table_name):
                        applied_rules.append(rule.rule_id)
                        if rule.deny:
                            return PolicyDecision(
                                allowed=False,
                                reason=f"Access denied by rule {rule.rule_id}",
                                applied_rules=applied_rules,
                            )

        # Check explicit denies
        denied_tables = user_context.get("denied_tables", [])
        if table_name in denied_tables:
            return PolicyDecision(
                allowed=False,
                reason="Table explicitly denied for user",
                applied_rules=applied_rules,
            )

        return PolicyDecision(
            allowed=True,
            reason="Access allowed",
            applied_rules=applied_rules,
        )

    def evaluate_sql(
        self,
        sql: str,
        user_context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Evaluate SQL for policy compliance.

        Args:
            sql: SQL query to evaluate
            user_context: User context

        Returns:
            Tuple of (is_safe, reason)
        """
        import re

        # Check for dangerous patterns
        for pattern in self.SQL_DANGEROUS_PATTERNS:
            if re.search(pattern, sql):
                self._log_policy_event(
                    "SQL_BLOCKED",
                    user_context.get("user_id"),
                    {"pattern": pattern, "sql": sql[:200]},
                )
                return False, f"SQL contains forbidden pattern: {pattern}"

        # Check for unauthorized tables
        denied_tables = user_context.get("denied_tables", [])
        for table in denied_tables:
            if re.search(rf"\b{table}\b", sql, re.IGNORECASE):
                self._log_policy_event(
                    "TABLE_ACCESS_DENIED",
                    user_context.get("user_id"),
                    {"table": table, "sql": sql[:200]},
                )
                return False, f"Access to table '{table}' is not permitted"

        # Check for PII columns
        pii_columns = ["ssn", "password", "credit_card", "salary"]
        for col in pii_columns:
            if re.search(rf"\b{col}\b", sql, re.IGNORECASE):
                # Check if user role allows PII
                roles = user_context.get("roles", [])
                if "CFO" not in roles and "Admin" not in roles:
                    self._log_policy_event(
                        "PII_ACCESS_DENIED",
                        user_context.get("user_id"),
                        {"column": col, "sql": sql[:200]},
                    )
                    return False, f"Access to column '{col}' requires elevated permissions"

        return True, "SQL passes policy checks"

    def get_row_filters(self, user_context: dict[str, Any]) -> dict[str, str]:
        """Get row-level security filters for user.

        Returns:
            Dict mapping table names to filter expressions
        """
        filters: dict[str, str] = {}

        roles = user_context.get("roles", [])

        # Regional Manager: filter by region
        if "Regional Manager" in roles:
            region = user_context.get("region", "UNKNOWN")
            filters["sales"] = f"region = '{region}'"
            filters["orders"] = f"region = '{region}'"
            filters["customers"] = f"region = '{region}'"

        # Sales Manager: filter by assigned regions/stores
        if "Sales Manager" in roles:
            assigned_stores = user_context.get("assigned_stores", [])
            if assigned_stores:
                store_list = "', '".join(assigned_stores)
                filters["sales"] = f"store_id IN ('{store_list}')"
                filters["orders"] = f"store_id IN ('{store_list}')"

        # Finance Analyst: filter to finance metrics only
        if "Finance Analyst" in roles:
            filters["metrics"] = "category = 'finance'"

        return filters

    def get_column_masks(self, user_context: dict[str, Any]) -> dict[str, list[str]]:
        """Get column-level masking rules.

        Returns:
            Dict mapping table names to masked column lists
        """
        masks: dict[str, list[str]] = {}

        roles = user_context.get("roles", [])

        # Default: mask PII for non-elevated roles
        if "CFO" not in roles and "Admin" not in roles and "HR" not in roles:
            masks["customers"] = ["ssn", "email", "phone", "address"]
            masks["employees"] = ["salary", "ssn", "personal_email"]
            masks["orders"] = ["customer_phone"]

        # Regional Manager: mask sensitive regional data
        if "Regional Manager" in roles:
            masks["regional_budgets"] = ["executive_bonus"]

        return masks

    def _matches_resource(self, pattern: str, resource: str) -> bool:
        """Check if resource matches pattern."""
        import re

        if pattern == "*":
            return True

        # Support comma-separated lists
        patterns = [p.strip() for p in pattern.split(",")]
        for p in patterns:
            if re.match(p.replace("*", ".*"), resource, re.IGNORECASE):
                return True

        return False

    def _log_policy_event(
        self,
        event_type: str,
        user_id: str,
        details: dict[str, Any],
    ) -> None:
        """Log a policy event for audit."""
        import uuid
        from datetime import UTC, datetime

        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "details": details,
        }
        self._audit_log.append(event)

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get audit log."""
        return self._audit_log.copy()
