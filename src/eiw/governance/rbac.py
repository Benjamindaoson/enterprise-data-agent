"""RBAC Engine for Enterprise Data Agent.

Role-Based Access Control implementation with:
- Role hierarchy
- Permission inheritance
- Role assignment validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResourceType(Enum):
    """Types of resources that can be protected."""

    METRIC = "metric"
    DIMENSION = "dimension"
    TABLE = "table"
    COLUMN = "column"
    FUNCTION = "function"
    REPORT = "report"
    DASHBOARD = "dashboard"


@dataclass
class Permission:
    """A single permission."""

    resource_type: ResourceType
    resource_id: str  # Can be wildcard "*"
    actions: list[str]  # read, write, delete, execute


@dataclass
class Role:
    """A role definition with permissions."""

    role_id: str
    name: str
    description: str
    permissions: list[Permission] = field(default_factory=list)
    parent_roles: list[str] = field(default_factory=list)  # Roles that inherit from this
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class User:
    """User with assigned roles."""

    user_id: str
    tenant_id: str
    roles: list[str] = field(default_factory=list)
    denied_permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RBACEngine:
    """Role-Based Access Control engine.

    Implements hierarchical RBAC with:
    - Role definitions
    - Permission inheritance
    - User-role assignment
    - Access evaluation
    """

    # Predefined enterprise roles
    ENTERPRISE_ROLES: dict[str, Role] = {
        "Admin": Role(
            role_id="admin",
            name="Administrator",
            description="Full system access",
            permissions=[
                Permission(ResourceType.METRIC, "*", ["read", "write", "delete"]),
                Permission(ResourceType.DIMENSION, "*", ["read", "write", "delete"]),
                Permission(ResourceType.TABLE, "*", ["read", "write", "delete"]),
                Permission(ResourceType.COLUMN, "*", ["read", "write", "delete"]),
                Permission(ResourceType.FUNCTION, "*", ["execute"]),
                Permission(ResourceType.REPORT, "*", ["read", "write", "delete"]),
                Permission(ResourceType.DASHBOARD, "*", ["read", "write", "delete"]),
            ],
        ),
        "CFO": Role(
            role_id="cfo",
            name="Chief Financial Officer",
            description="Full financial data access",
            permissions=[
                Permission(ResourceType.METRIC, "*", ["read"]),
                Permission(ResourceType.DIMENSION, "*", ["read"]),
                Permission(ResourceType.TABLE, "*", ["read"]),
                Permission(ResourceType.COLUMN, "*", ["read"]),
                Permission(ResourceType.FUNCTION, ["financial_analysis", "reporting"], ["execute"]),
                Permission(ResourceType.REPORT, "*", ["read", "write"]),
            ],
        ),
        "Finance Analyst": Role(
            role_id="finance_analyst",
            name="Finance Analyst",
            description="Standard financial analysis access",
            permissions=[
                Permission(ResourceType.METRIC, ["revenue", "gross_profit", "net_income", "expenses"], ["read"]),
                Permission(ResourceType.DIMENSION, "*", ["read"]),
                Permission(ResourceType.TABLE, ["fact_finance", "dim_account"], ["read"]),
                Permission(ResourceType.FUNCTION, ["financial_analysis", "reporting"], ["execute"]),
                Permission(ResourceType.REPORT, ["financial", "management"], ["read", "write"]),
            ],
        ),
        "Regional Manager": Role(
            role_id="regional_manager",
            name="Regional Manager",
            description="Region-scoped business access",
            permissions=[
                Permission(ResourceType.METRIC, ["sales", "orders", "conversions"], ["read"]),
                Permission(ResourceType.DIMENSION, ["region", "store", "product", "channel"], ["read"]),
                Permission(ResourceType.TABLE, ["fact_sales", "dim_store"], ["read"]),
                Permission(ResourceType.FUNCTION, ["regional_analysis"], ["execute"]),
                Permission(ResourceType.REPORT, ["regional", "operational"], ["read"]),
            ],
        ),
        "Sales Manager": Role(
            role_id="sales_manager",
            name="Sales Manager",
            description="Sales team management access",
            permissions=[
                Permission(ResourceType.METRIC, ["sales", "orders", "conversions", "customers"], ["read"]),
                Permission(ResourceType.DIMENSION, ["region", "product", "channel"], ["read"]),
                Permission(ResourceType.TABLE, ["fact_sales", "dim_product", "dim_channel"], ["read"]),
                Permission(ResourceType.COLUMN, ["customers"], ["read"]),  # No PII
                Permission(ResourceType.FUNCTION, ["sales_analysis"], ["execute"]),
                Permission(ResourceType.REPORT, ["sales", "performance"], ["read"]),
            ],
        ),
        "Data Scientist": Role(
            role_id="data_scientist",
            name="Data Scientist",
            description="Analytical access with Python execution",
            permissions=[
                Permission(ResourceType.METRIC, "*", ["read"]),
                Permission(ResourceType.DIMENSION, "*", ["read"]),
                Permission(ResourceType.TABLE, "*", ["read"]),
                Permission(ResourceType.COLUMN, "*", ["read"]),
                Permission(ResourceType.FUNCTION, ["analysis", "reporting", "python_sandbox"], ["execute"]),
                Permission(ResourceType.REPORT, "*", ["read"]),
            ],
        ),
        "Business User": Role(
            role_id="business_user",
            name="Business User",
            description="Basic read-only access",
            permissions=[
                Permission(ResourceType.METRIC, ["sales", "orders", "customers"], ["read"]),
                Permission(ResourceType.DIMENSION, ["region", "product"], ["read"]),
                Permission(ResourceType.TABLE, ["fact_sales"], ["read"]),
                Permission(ResourceType.FUNCTION, ["basic_reporting"], ["execute"]),
                Permission(ResourceType.REPORT, ["public"], ["read"]),
            ],
        ),
    }

    def __init__(self) -> None:
        """Initialize RBAC engine."""
        self._roles: dict[str, Role] = self.ENTERPRISE_ROLES.copy()
        self._users: dict[str, User] = {}

    def register_role(self, role: Role) -> None:
        """Register a new role."""
        self._roles[role.role_id] = role

    def assign_role(self, user_id: str, role_id: str) -> None:
        """Assign a role to a user."""
        if role_id not in self._roles:
            raise ValueError(f"Unknown role: {role_id}")

        if user_id not in self._users:
            self._users[user_id] = User(user_id=user_id, tenant_id="default")

        if role_id not in self._users[user_id].roles:
            self._users[user_id].roles.append(role_id)

    def revoke_role(self, user_id: str, role_id: str) -> None:
        """Revoke a role from a user."""
        if user_id in self._users:
            if role_id in self._users[user_id].roles:
                self._users[user_id].roles.remove(role_id)

    def get_user_roles(self, user_id: str) -> list[Role]:
        """Get all roles assigned to a user, including inherited."""
        if user_id not in self._users:
            return []

        roles: list[Role] = []
        seen: set[str] = set()

        def collect_roles(role_ids: list[str]) -> None:
            for role_id in role_ids:
                if role_id in seen:
                    continue
                seen.add(role_id)
                role = self._roles.get(role_id)
                if role:
                    roles.append(role)
                    collect_roles(role.parent_roles)

        collect_roles(self._users[user_id].roles)
        return roles

    def has_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: str,
    ) -> bool:
        """Check if user has permission for an action on a resource.

        Args:
            user_id: User identifier
            resource_type: Type of resource
            resource_id: Resource identifier (can be wildcard)
            action: Action to perform (read, write, delete, execute)

        Returns:
            True if permission is granted
        """
        if user_id not in self._users:
            return False

        user = self._users[user_id]
        roles = self.get_user_roles(user_id)

        # Check inherited roles from user object
        for role_id in user.roles:
            if role_id in self._roles:
                roles.append(self._roles[role_id])

        # Collect all permissions
        all_permissions: list[Permission] = []
        for role in roles:
            all_permissions.extend(role.permissions)

        # Check for permission
        for perm in all_permissions:
            if perm.resource_type != resource_type:
                continue

            if not self._matches_resource(perm.resource_id, resource_id):
                continue

            if action in perm.actions:
                # Check for explicit denial
                if f"{resource_type.value}:{resource_id}:{action}" in user.denied_permissions:
                    return False
                return True

        return False

    def evaluate_access(
        self,
        user_id: str,
        required_permissions: list[tuple[ResourceType, str, str]],
    ) -> tuple[bool, list[str]]:
        """Evaluate if user has all required permissions.

        Args:
            user_id: User identifier
            required_permissions: List of (resource_type, resource_id, action) tuples

        Returns:
            Tuple of (all_granted, list of denied permissions)
        """
        denied: list[str] = []

        for resource_type, resource_id, action in required_permissions:
            if not self.has_permission(user_id, resource_type, resource_id, action):
                denied.append(f"{resource_type.value}:{resource_id}:{action}")

        return len(denied) == 0, denied

    def get_user_context(self, user_id: str) -> dict[str, Any]:
        """Get user context for policy engine.

        Returns:
            User context dictionary
        """
        if user_id not in self._users:
            return {
                "user_id": user_id,
                "roles": [],
                "allowed_metric_ids": [],
                "allowed_dimension_ids": [],
            }

        user = self._users[user_id]
        roles = self.get_user_roles(user_id)

        # Collect allowed metrics and dimensions
        allowed_metrics: set[str] = set()
        allowed_dimensions: set[str] = set()
        allowed_tables: set[str] = set()
        denied_tables: set[str] = set()

        for role in roles:
            for perm in role.permissions:
                if perm.resource_type == ResourceType.METRIC:
                    if perm.resource_id == "*":
                        allowed_metrics.add("*")
                    else:
                        for r in perm.resource_id:
                            allowed_metrics.add(r.strip())
                elif perm.resource_type == ResourceType.DIMENSION:
                    if perm.resource_id == "*":
                        allowed_dimensions.add("*")
                    else:
                        for r in perm.resource_id:
                            allowed_dimensions.add(r.strip())
                elif perm.resource_type == ResourceType.TABLE:
                    if "read" in perm.actions:
                        for r in perm.resource_id:
                            allowed_tables.add(r.strip())
                    else:
                        for r in perm.resource_id:
                            denied_tables.add(r.strip())

        return {
            "user_id": user_id,
            "tenant_id": user.tenant_id,
            "roles": user.roles,
            "allowed_metric_ids": list(allowed_metrics),
            "allowed_dimension_ids": list(allowed_dimensions),
            "allowed_tables": list(allowed_tables),
            "denied_tables": list(denied_tables),
        }

    def _matches_resource(self, pattern: str, resource: str) -> bool:
        """Check if resource matches pattern."""
        import re

        if pattern == "*":
            return True

        # Handle list of resources
        patterns = [p.strip() for p in pattern.split(",")]
        for p in patterns:
            if re.match(f"^{p.replace('*', '.*')}$", resource, re.IGNORECASE):
                return True

        return False
