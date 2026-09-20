"""Audit Logger for Enterprise Data Agent.

Comprehensive audit logging for:
- All data access events
- Policy decisions
- Security events
- Agent operations
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AuditEventType(Enum):
    """Types of auditable events."""

    # Data access
    QUERY_EXECUTED = "query_executed"
    METRIC_ACCESSED = "metric_accessed"
    TABLE_ACCESSED = "table_accessed"
    COLUMN_ACCESSED = "column_accessed"

    # Policy decisions
    POLICY_ALLOWED = "policy_allowed"
    POLICY_DENIED = "policy_denied"
    PERMISSION_CHECKED = "permission_checked"

    # Security
    SQL_BLOCKED = "sql_blocked"
    INJECTION_ATTEMPT = "injection_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PII_ACCESSED = "pii_accessed"

    # Agent operations
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TOOL_EXECUTED = "tool_executed"
    HYPOTHESIS_TESTED = "hypothesis_tested"

    # Evaluation
    EVALUATION_RUN = "evaluation_run"
    EVALUATION_PASSED = "evaluation_passed"
    EVALUATION_FAILED = "evaluation_failed"


@dataclass
class AuditEvent:
    """A single audit event."""

    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    actor_id: str  # user_id or system
    resource_type: str
    resource_id: str
    action: str
    outcome: str  # SUCCESS, DENIED, ERROR
    details: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


class AuditLogger:
    """Comprehensive audit logger for Enterprise Data Agent.

    This logger captures:
    - All data access events
    - Policy decisions and enforcement
    - Security events
    - Agent operations
    - Evaluation results

    In production, this would write to:
    - PostgreSQL (for querying)
    - Elasticsearch (for search)
    - S3/GCS (for long-term storage)
    - SIEM systems (for security analysis)
    """

    def __init__(self, storage_path: str | None = None) -> None:
        """Initialize audit logger.

        Args:
            storage_path: Path for local audit storage (optional)
        """
        self._events: list[AuditEvent] = []
        self._storage_path = storage_path

    def log(
        self,
        event_type: AuditEventType,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        outcome: str,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> str:
        """Log an audit event.

        Args:
            event_type: Type of event
            actor_id: User or system ID
            resource_type: Type of resource accessed
            resource_id: Identifier of resource
            action: Action performed
            outcome: Result (SUCCESS, DENIED, ERROR)
            details: Additional event details
            trace_id: OpenTelemetry trace ID
            span_id: OpenTelemetry span ID

        Returns:
            Event ID
        """
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC),
            event_type=event_type,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            details=details or {},
            trace_id=trace_id,
            span_id=span_id,
        )

        self._events.append(event)
        self._persist_event(event)

        return event.event_id

    def log_query(
        self,
        user_id: str,
        sql: str,
        tables: list[str],
        row_count: int,
        execution_time_ms: float,
        trace_id: str | None = None,
    ) -> str:
        """Log a query execution event."""
        return self.log(
            event_type=AuditEventType.QUERY_EXECUTED,
            actor_id=user_id,
            resource_type="query",
            resource_id=self._hash_sql(sql),
            action="execute",
            outcome="SUCCESS",
            details={
                "sql": sql[:1000],  # Truncate for storage
                "tables": tables,
                "row_count": row_count,
                "execution_time_ms": execution_time_ms,
            },
            trace_id=trace_id,
        )

    def log_policy_decision(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        allowed: bool,
        reason: str,
        applied_rules: list[str],
    ) -> str:
        """Log a policy decision."""
        return self.log(
            event_type=AuditEventType.POLICY_DENIED if not allowed else AuditEventType.POLICY_ALLOWED,
            actor_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome="SUCCESS" if allowed else "DENIED",
            details={
                "reason": reason,
                "applied_rules": applied_rules,
            },
        )

    def log_security_event(
        self,
        event_type: AuditEventType,
        user_id: str | None,
        description: str,
        details: dict[str, Any],
    ) -> str:
        """Log a security-relevant event."""
        return self.log(
            event_type=event_type,
            actor_id=user_id or "anonymous",
            resource_type="security",
            resource_id="",
            action="security_event",
            outcome="ALERT",
            details={
                "description": description,
                **details,
            },
        )

    def log_agent_operation(
        self,
        task_id: str,
        operation: str,
        outcome: str,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> str:
        """Log an agent operation."""
        return self.log(
            event_type=AuditEventType.TASK_COMPLETED if outcome == "SUCCESS" else AuditEventType.TASK_FAILED,
            actor_id="agent",
            resource_type="task",
            resource_id=task_id,
            action=operation,
            outcome=outcome,
            details=details or {},
            trace_id=trace_id,
        )

    def _hash_sql(self, sql: str) -> str:
        """Create a hash of SQL for identification."""
        import hashlib
        return hashlib.sha256(sql.encode()).hexdigest()[:16]

    def _persist_event(self, event: AuditEvent) -> None:
        """Persist event to storage."""
        if self._storage_path:
            # In production, this would write to a database
            # For now, we'll just keep in memory
            pass

    def query(
        self,
        actor_id: str | None = None,
        event_types: list[AuditEventType] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        resource_type: str | None = None,
        outcome: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events.

        Args:
            actor_id: Filter by actor
            event_types: Filter by event types
            start_time: Filter by start time
            end_time: Filter by end time
            resource_type: Filter by resource type
            outcome: Filter by outcome
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        results = self._events

        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]

        if event_types:
            results = [e for e in results if e.event_type in event_types]

        if start_time:
            results = [e for e in results if e.timestamp >= start_time]

        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]

        if outcome:
            results = [e for e in results if e.outcome == outcome]

        # Sort by timestamp descending
        results = sorted(results, key=lambda e: e.timestamp, reverse=True)

        return results[:limit]

    def get_security_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditEvent]:
        """Get all security-related events."""
        security_types = [
            AuditEventType.SQL_BLOCKED,
            AuditEventType.INJECTION_ATTEMPT,
            AuditEventType.UNAUTHORIZED_ACCESS,
            AuditEventType.PII_ACCESSED,
        ]
        return self.query(
            event_types=security_types,
            start_time=start_time,
            end_time=end_time,
        )

    def get_data_access_summary(
        self,
        user_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get a summary of data access for a user."""
        events = self.query(
            actor_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        # Aggregate by resource type
        by_resource: dict[str, int] = {}
        by_outcome: dict[str, int] = {"SUCCESS": 0, "DENIED": 0, "ERROR": 0}
        tables_accessed: set[str] = set()

        for event in events:
            by_resource[event.resource_type] = by_resource.get(event.resource_type, 0) + 1
            by_outcome[event.outcome] = by_outcome.get(event.outcome, 0) + 1

            if event.resource_type == "table" and event.resource_id:
                tables_accessed.add(event.resource_id)

        return {
            "user_id": user_id,
            "total_events": len(events),
            "by_resource_type": by_resource,
            "by_outcome": by_outcome,
            "tables_accessed": list(tables_accessed),
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            },
        }

    def export_events(
        self,
        format: str = "json",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> str:
        """Export events to specified format.

        Args:
            format: Export format (json, csv)
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            Exported data as string
        """
        import json

        events = self.query(start_time=start_time, end_time=end_time, limit=100000)

        if format == "json":
            return json.dumps(
                [
                    {
                        "event_id": e.event_id,
                        "timestamp": e.timestamp.isoformat(),
                        "event_type": e.event_type.value,
                        "actor_id": e.actor_id,
                        "resource_type": e.resource_type,
                        "resource_id": e.resource_id,
                        "action": e.action,
                        "outcome": e.outcome,
                        "details": e.details,
                    }
                    for e in events
                ],
                indent=2,
            )

        elif format == "csv":
            lines = [
                "event_id,timestamp,event_type,actor_id,resource_type,resource_id,action,outcome"
            ]
            for e in events:
                lines.append(
                    f"{e.event_id},{e.timestamp.isoformat()},{e.event_type.value},"
                    f"{e.actor_id},{e.resource_type},{e.resource_id},{e.action},{e.outcome}"
                )
            return "\n".join(lines)

        return ""
