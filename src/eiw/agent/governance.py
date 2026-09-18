"""RBAC and Governance - Role-Based Access Control.

This module provides:
- Role definitions
- Permission system
- Access control
- Audit logging
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "governance")


# =============================================================================
# Role and Permission Types
# =============================================================================


class Role(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"  # Full access
    ANALYST = "analyst"  # Standard analysis access
    VIEWER = "viewer"  # Read-only access
    DATA_ENGINEER = "data_engineer"  # Schema access
    FINANCE = "finance"  # Finance domain
    SALES = "sales"  # Sales domain
    OPERATIONS = "operations"  # Operations domain


class Permission(str, Enum):
    """Permissions."""

    # Data access
    READ_ANY_SCHEMA = "read_any_schema"
    READ_FINANCE_SCHEMA = "read_finance_schema"
    READ_SALES_SCHEMA = "read_sales_schema"
    READ_OPERATIONS_SCHEMA = "read_operations_schema"

    # Query execution
    EXECUTE_QUERY = "execute_query"
    EXECUTE_NL2SQL = "execute_nl2sql"
    EXECUTE_DETERMINISTIC = "execute_deterministic"

    # Analysis tools
    USE_TREND_TOOLS = "use_trend_tools"
    USE_COMPARISON_TOOLS = "use_comparison_tools"
    USE_CONTRIBUTION_TOOLS = "use_contribution_tools"
    USE_PVM_TOOLS = "use_pvm_tools"
    USE_VARIANCE_TOOLS = "use_variance_tools"
    USE_DRILLDOWN_TOOLS = "use_drilldown_tools"
    USE_ANOMALY_TOOLS = "use_anomaly_tools"
    USE_PYTHON_TOOLS = "use_python_tools"

    # Administrative
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOG = "view_audit_log"
    EXPORT_DATA = "export_data"


# =============================================================================
# Role Definitions
# =============================================================================

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: {
        # All permissions
        Permission.READ_ANY_SCHEMA,
        Permission.READ_FINANCE_SCHEMA,
        Permission.READ_SALES_SCHEMA,
        Permission.READ_OPERATIONS_SCHEMA,
        Permission.EXECUTE_QUERY,
        Permission.EXECUTE_NL2SQL,
        Permission.EXECUTE_DETERMINISTIC,
        Permission.USE_TREND_TOOLS,
        Permission.USE_COMPARISON_TOOLS,
        Permission.USE_CONTRIBUTION_TOOLS,
        Permission.USE_PVM_TOOLS,
        Permission.USE_VARIANCE_TOOLS,
        Permission.USE_DRILLDOWN_TOOLS,
        Permission.USE_ANOMALY_TOOLS,
        Permission.USE_PYTHON_TOOLS,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOG,
        Permission.EXPORT_DATA,
    },
    Role.ANALYST: {
        Permission.READ_ANY_SCHEMA,
        Permission.EXECUTE_QUERY,
        Permission.EXECUTE_NL2SQL,
        Permission.EXECUTE_DETERMINISTIC,
        Permission.USE_TREND_TOOLS,
        Permission.USE_COMPARISON_TOOLS,
        Permission.USE_CONTRIBUTION_TOOLS,
        Permission.USE_PVM_TOOLS,
        Permission.USE_VARIANCE_TOOLS,
        Permission.USE_DRILLDOWN_TOOLS,
        Permission.USE_ANOMALY_TOOLS,
        Permission.USE_PYTHON_TOOLS,
        Permission.EXPORT_DATA,
    },
    Role.VIEWER: {
        Permission.READ_ANY_SCHEMA,
        Permission.EXECUTE_DETERMINISTIC,
    },
    Role.DATA_ENGINEER: {
        Permission.READ_ANY_SCHEMA,
        Permission.EXECUTE_DETERMINISTIC,
    },
    Role.FINANCE: {
        Permission.READ_FINANCE_SCHEMA,
        Permission.EXECUTE_QUERY,
        Permission.EXECUTE_NL2SQL,
        Permission.EXECUTE_DETERMINISTIC,
        Permission.USE_VARIANCE_TOOLS,
        Permission.USE_CONTRIBUTION_TOOLS,
        Permission.USE_PVM_TOOLS,
        Permission.EXPORT_DATA,
    },
    Role.SALES: {
        Permission.READ_SALES_SCHEMA,
        Permission.EXECUTE_QUERY,
        Permission.EXECUTE_NL2SQL,
        Permission.EXECUTE_DETERMINISTIC,
        Permission.USE_TREND_TOOLS,
        Permission.USE_COMPARISON_TOOLS,
        Permission.USE_DRILLDOWN_TOOLS,
        Permission.EXPORT_DATA,
    },
    Role.OPERATIONS: {
        Permission.READ_OPERATIONS_SCHEMA,
        Permission.EXECUTE_QUERY,
        Permission.EXECUTE_NL2SQL,
        Permission.EXECUTE_DETERMINISTIC,
        Permission.USE_TREND_TOOLS,
        Permission.USE_ANOMALY_TOOLS,
        Permission.USE_DRILLDOWN_TOOLS,
        Permission.EXPORT_DATA,
    },
}


# =============================================================================
# User and Session
# =============================================================================


@dataclass
class User:
    """User entity."""

    user_id: str
    username: str
    email: str
    roles: list[Role] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: datetime | None = None

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a permission."""
        for role in self.roles:
            if permission in ROLE_PERMISSIONS.get(role, set()):
                return True
        return False

    def has_role(self, role: Role) -> bool:
        """Check if user has a role."""
        return role in self.roles

    def can_access_domain(self, domain: str) -> bool:
        """Check if user can access a domain."""
        domain_permission_map = {
            "finance": Permission.READ_FINANCE_SCHEMA,
            "sales": Permission.READ_SALES_SCHEMA,
            "operations": Permission.READ_OPERATIONS_SCHEMA,
        }

        perm = domain_permission_map.get(domain.lower())
        if not perm:
            return True  # Unknown domain, allow

        return self.has_permission(Permission.READ_ANY_SCHEMA) or self.has_permission(perm)


class Session(BaseModel):
    """User session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Unique session ID")
    user_id: str = Field(description="User ID")
    username: str = Field(description="Username")
    roles: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)

    def has_permission(self, permission: str) -> bool:
        """Check if session has a permission."""
        perm = Permission(permission) if isinstance(permission, str) else permission
        for role_str in self.roles:
            role = Role(role_str) if isinstance(role_str, str) else role_str
            if perm in ROLE_PERMISSIONS.get(role, set()):
                return True
        return False


# =============================================================================
# Audit Log
# =============================================================================


class AuditEventType(str, Enum):
    """Audit event types."""

    LOGIN = "login"
    LOGOUT = "logout"
    QUERY_EXECUTED = "query_executed"
    QUERY_REJECTED = "query_rejected"
    PERMISSION_DENIED = "permission_denied"
    DATA_EXPORTED = "data_exported"
    CONFIG_CHANGED = "config_changed"
    USER_CREATED = "user_created"
    USER_MODIFIED = "user_modified"


@dataclass
class AuditEvent:
    """An audit event."""

    event_id: str
    event_type: AuditEventType
    user_id: str
    session_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    resource: str | None = None
    action: str | None = None
    result: str | None = None  # success, denied, failed
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "resource": self.resource,
            "action": self.action,
            "result": self.result,
            "details": self.details,
            "ip_address": self.ip_address,
        }


# =============================================================================
# Access Control
# =============================================================================


class AccessControl:
    """Access control enforcement."""

    def __init__(self):
        """Initialize access control."""
        self._audit_log: list[AuditEvent] = []

    def check_permission(
        self,
        session: Session,
        permission: Permission,
        resource: str | None = None,
    ) -> bool:
        """Check if session has permission.

        Args:
            session: User session
            permission: Permission to check
            resource: Optional resource being accessed

        Returns:
            True if allowed
        """
        allowed = session.has_permission(permission)

        # Log the check
        self._log_event(
            event_type=AuditEventType.PERMISSION_DENIED if not allowed else AuditEventType.QUERY_EXECUTED,
            user_id=session.user_id,
            session_id=session.session_id,
            resource=resource,
            action=permission.value,
            result="denied" if not allowed else "success",
        )

        if not allowed:
            logger.warning(
                f"Permission denied: {permission.value}",
                extra={"user_id": session.user_id, "resource": resource}
            )

        return allowed

    def check_domain_access(
        self,
        session: Session,
        domain: str,
    ) -> bool:
        """Check if session can access a domain.

        Args:
            session: User session
            domain: Domain to access

        Returns:
            True if allowed
        """
        # Check domain-specific permission
        domain_perms = {
            "finance": Permission.READ_FINANCE_SCHEMA,
            "sales": Permission.READ_SALES_SCHEMA,
            "operations": Permission.READ_OPERATIONS_SCHEMA,
        }

        perm = domain_perms.get(domain.lower())

        if perm:
            # Check if user has domain permission or READ_ANY_SCHEMA
            return session.has_permission(Permission.READ_ANY_SCHEMA) or session.has_permission(perm)

        return True

    def can_use_tool(self, session: Session, tool_name: str) -> bool:
        """Check if session can use a tool.

        Args:
            session: User session
            tool_name: Tool name

        Returns:
            True if allowed
        """
        tool_permission_map = {
            "nl2sql_query": Permission.EXECUTE_NL2SQL,
            "trend_analysis": Permission.USE_TREND_TOOLS,
            "period_comparison": Permission.USE_COMPARISON_TOOLS,
            "contribution_analysis": Permission.USE_CONTRIBUTION_TOOLS,
            "price_volume_mix": Permission.USE_PVM_TOOLS,
            "variance_analysis": Permission.USE_VARIANCE_TOOLS,
            "drilldown": Permission.USE_DRILLDOWN_TOOLS,
            "anomaly_detection": Permission.USE_ANOMALY_TOOLS,
            "python_analysis": Permission.USE_PYTHON_TOOLS,
        }

        perm = tool_permission_map.get(tool_name)
        if not perm:
            return True  # Unknown tool, allow

        return self.check_permission(session, perm, f"tool:{tool_name}")

    def can_export_data(self, session: Session) -> bool:
        """Check if session can export data.

        Args:
            session: User session

        Returns:
            True if allowed
        """
        return self.check_permission(session, Permission.EXPORT_DATA, "export")

    def _log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        session_id: str,
        resource: str | None = None,
        action: str | None = None,
        result: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event.

        Args:
            event_type: Type of event
            user_id: User ID
            session_id: Session ID
            resource: Resource accessed
            action: Action performed
            result: Result
            details: Additional details
        """
        import uuid

        event = AuditEvent(
            event_id=f"audit_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
        )

        self._audit_log.append(event)

        logger.info(
            f"Audit: {event_type.value}",
            extra={
                "event_id": event.event_id,
                "user_id": user_id,
                "result": result,
            }
        )

    def get_audit_log(
        self,
        user_id: str | None = None,
        event_type: AuditEventType | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit log entries.

        Args:
            user_id: Filter by user
            event_type: Filter by event type
            limit: Maximum entries

        Returns:
            List of audit events
        """
        events = self._audit_log

        if user_id:
            events = [e for e in events if e.user_id == user_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Return most recent
        return [e.to_dict() for e in events[-limit:]]


# =============================================================================
# Demo Personas
# =============================================================================


def create_demo_personas() -> dict[str, User]:
    """Create demo personas for testing.

    Returns:
        Dict of user_id -> User
    """
    return {
        "admin": User(
            user_id="admin",
            username="admin",
            email="admin@example.com",
            roles=[Role.ADMIN],
        ),
        "analyst_alice": User(
            user_id="analyst_alice",
            username="alice.analyst",
            email="alice@example.com",
            roles=[Role.ANALYST],
        ),
        "viewer_bob": User(
            user_id="viewer_bob",
            username="bob.viewer",
            email="bob@example.com",
            roles=[Role.VIEWER],
        ),
        "finance_carol": User(
            user_id="finance_carol",
            username="carol.finance",
            email="carol@example.com",
            roles=[Role.FINANCE],
        ),
        "sales_david": User(
            user_id="sales_david",
            username="david.sales",
            email="david@example.com",
            roles=[Role.SALES],
        ),
        "ops_eve": User(
            user_id="ops_eve",
            username="eve.ops",
            email="eve@example.com",
            roles=[Role.OPERATIONS],
        ),
    }


def create_demo_session(user: User) -> Session:
    """Create a session for a demo user.

    Args:
        user: User to create session for

    Returns:
        Session
    """
    import uuid

    return Session(
        session_id=f"sess_{uuid.uuid4().hex[:8]}",
        user_id=user.user_id,
        username=user.username,
        roles=[r.value for r in user.roles],
    )


# =============================================================================
# Governance Configuration
# =============================================================================


class GovernanceConfig(BaseModel):
    """Configuration for governance."""

    model_config = ConfigDict(extra="forbid")

    enable_rbac: bool = Field(default=True)
    enable_audit_log: bool = Field(default=True)
    require_authentication: bool = Field(default=True)
    max_query_timeout_seconds: int = Field(default=60)
    max_export_rows: int = Field(default=10000)
    allowed_export_formats: list[str] = Field(
        default_factory=lambda: ["csv", "json", "xlsx"]
    )


def create_governance_config(
    enable_rbac: bool = True,
    enable_audit: bool = True,
) -> GovernanceConfig:
    """Create governance config.

    Args:
        enable_rbac: Enable RBAC
        enable_audit: Enable audit logging

    Returns:
        Governance config
    """
    return GovernanceConfig(
        enable_rbac=enable_rbac,
        enable_audit_log=enable_audit,
    )
