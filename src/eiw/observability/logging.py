"""Structured logging for Enterprise Data Agent.

Provides correlation-aware structured logging that integrates with OpenTelemetry.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from eiw.observability.otel import (
    get_correlation_context,
    filter_sensitive_fields,
    SENSITIVE_FIELDS,
)


# =============================================================================
# Log levels and formats
# =============================================================================


class LogLevel:
    """Log levels matching OTel severity."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


# =============================================================================
# Structured log record
# =============================================================================


class StructuredLogRecord(logging.LogRecord):
    """Enhanced log record with structured fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correlation_id: str | None = None
        self.trace_id: str | None = None
        self.task_id: str | None = None
        self.span_id: str | None = None
        self.component: str | None = None
        self.event: str | None = None
        self.duration_ms: float | None = None
        self.status: str | None = None
        self.error_category: str | None = None
        self.metric_ids: list[str] = []
        self.dimension_ids: list[str] = []
        self.tool_name: str | None = None
        self.validation_status: str | None = None


# =============================================================================
# JSON formatter
# =============================================================================


class StructuredJsonFormatter(logging.Formatter):
    """Formats logs as structured JSON for machine consumption."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        ctx = get_correlation_context()

        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": ctx.correlation_id,
            "trace_id": ctx.trace_id,
            "task_id": ctx.task_id,
        }

        # Add structured fields if present
        if isinstance(record, StructuredLogRecord):
            if record.trace_id:
                log_data["trace_id"] = record.trace_id
            if record.task_id:
                log_data["task_id"] = record.task_id
            if record.span_id:
                log_data["span_id"] = record.span_id
            if record.component:
                log_data["component"] = record.component
            if record.event:
                log_data["event"] = record.event
            if record.duration_ms is not None:
                log_data["duration_ms"] = record.duration_ms
            if record.status:
                log_data["status"] = record.status
            if record.error_category:
                log_data["error_category"] = record.error_category
            if record.metric_ids:
                log_data["metric_ids"] = record.metric_ids
            if record.dimension_ids:
                log_data["dimension_ids"] = record.dimension_ids
            if record.tool_name:
                log_data["tool_name"] = record.tool_name
            if record.validation_status:
                log_data["validation_status"] = record.validation_status

        # Add extra fields (filtered)
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in logging.makeLogRecord({}).__dict__
            and not k.startswith("_")
        }
        filtered_extra = filter_sensitive_fields(extra_fields)
        log_data["extra"] = filtered_extra

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


# =============================================================================
# Human-readable formatter
# =============================================================================


class StructuredTextFormatter(logging.Formatter):
    """Formats logs for human readability during development."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as readable text."""
        ctx = get_correlation_context()

        # Base timestamp and level
        parts = [
            f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]",
            f"[{record.levelname:5s}]",
        ]

        # Add correlation context
        corr_parts = []
        if ctx.correlation_id:
            corr_parts.append(f"corr={ctx.correlation_id[:8]}")
        if ctx.trace_id:
            corr_parts.append(f"trace={ctx.trace_id[:16]}")
        if ctx.task_id:
            corr_parts.append(f"task={ctx.task_id[:8]}")

        if corr_parts:
            parts.append(f"[{' '.join(corr_parts)}]")

        # Add component and event
        if isinstance(record, StructuredLogRecord):
            if record.component:
                parts.append(f"[{record.component}]")
            if record.event:
                parts.append(f"event={record.event}")
            if record.duration_ms is not None:
                parts.append(f"duration={record.duration_ms:.2f}ms")
            if record.status:
                parts.append(f"status={record.status}")
            if record.tool_name:
                parts.append(f"tool={record.tool_name}")

        # Add message
        parts.append(record.getMessage())

        # Add extra fields (filtered, non-sensitive)
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in logging.makeLogRecord({}).__dict__:
                continue
            if key.lower() in SENSITIVE_FIELDS:
                continue
            extra_fields[key] = value

        if extra_fields:
            parts.append(f"{json.dumps(extra_fields, default=str)}")

        return " ".join(parts)


# =============================================================================
# Logger factory
# =============================================================================


class EnterpriseLoggerFactory:
    """Factory for creating enterprise-structured loggers."""

    def __init__(self) -> None:
        self._loggers: dict[str, logging.Logger] = {}
        self._json_mode = False

    def set_json_mode(self, enabled: bool) -> None:
        """Enable/disable JSON output mode."""
        self._json_mode = enabled

    def get_logger(self, name: str, component: str | None = None) -> logging.Logger:
        """Get or create a logger with structured logging.

        Args:
            name: Logger name (typically module path)
            component: Component name for correlation

        Returns:
            Configured logger
        """
        if name in self._loggers:
            logger = self._loggers[name]
            if component:
                logger = logging.LoggerAdapter(logger, {"component": component})
            return logger

        logger = logging.getLogger(name)

        # Set level
        logger.setLevel(logging.DEBUG if self._json_mode else logging.INFO)

        # Clear existing handlers
        logger.handlers.clear()

        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        # Set formatter
        if self._json_mode:
            formatter = StructuredJsonFormatter()
        else:
            formatter = StructuredTextFormatter()

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent propagation to root logger
        logger.propagate = False

        self._loggers[name] = logger
        return logger


# Global factory
_logger_factory = EnterpriseLoggerFactory()


def set_structured_logging_json(enabled: bool) -> None:
    """Enable/disable JSON structured logging globally."""
    _logger_factory.set_json_mode(enabled)


def get_structured_logger(
    name: str,
    component: str | None = None,
) -> logging.LoggerAdapter:
    """Get a structured logger.

    Args:
        name: Logger name (typically __name__)
        component: Component name (e.g., "intent_resolver", "planner")

    Returns:
        Logger adapter with structured logging support
    """
    logger = _logger_factory.get_logger(name, component)
    return logging.LoggerAdapter(logger, {"component": component or name.split(".")[-1]})


# =============================================================================
# Convenience logging functions
# =============================================================================


def log_task_event(
    event: str,
    message: str,
    task_id: str | None = None,
    component: str | None = None,
    status: str = "OK",
    duration_ms: float | None = None,
    **extra: Any,
) -> None:
    """Log a structured task event.

    Args:
        event: Event name (e.g., "intent_resolved", "tool_executed")
        message: Human-readable message
        task_id: Associated task ID
        component: Component that generated the event
        status: Event status (OK, ERROR, WARN)
        duration_ms: Operation duration
        **extra: Additional structured fields
    """
    ctx = get_correlation_context()

    extra_filtered = filter_sensitive_fields(extra)

    log_data = {
        "event": event,
        "correlation_id": ctx.correlation_id,
        "trace_id": ctx.trace_id,
        "task_id": task_id or ctx.task_id,
        "status": status,
        "duration_ms": duration_ms,
        **extra_filtered,
    }

    logger = get_structured_logger("eiw.task", component)
    logger.info(f"{event}: {message}", extra=log_data)


def log_tool_execution(
    tool_name: str,
    status: str,
    duration_ms: float,
    task_id: str | None = None,
    correlation_id: str | None = None,
    row_count: int | None = None,
    error_category: str | None = None,
    **extra: Any,
) -> None:
    """Log a tool execution event.

    Args:
        tool_name: Name of the executed tool
        status: Execution status (OK, ERROR)
        duration_ms: Execution duration
        task_id: Associated task ID
        correlation_id: Correlation ID
        row_count: Number of rows returned
        error_category: Error category if failed
        **extra: Additional structured fields
    """
    ctx = get_correlation_context()

    extra_filtered = filter_sensitive_fields(extra)

    log_data = {
        "event": "tool_execution",
        "tool_name": tool_name,
        "correlation_id": correlation_id or ctx.correlation_id,
        "trace_id": ctx.trace_id,
        "task_id": task_id or ctx.task_id,
        "status": status,
        "duration_ms": duration_ms,
        "row_count": row_count,
        "error_category": error_category,
        **extra_filtered,
    }

    logger = get_structured_logger("eiw.tools", "tool_executor")
    logger.info(f"Tool executed: {tool_name} ({status}, {duration_ms:.2f}ms)", extra=log_data)


def log_validation(
    validation_status: str,
    rule_id: str,
    subject_type: str,
    details: str,
    task_id: str | None = None,
    passed: bool = True,
    **extra: Any,
) -> None:
    """Log a validation event.

    Args:
        validation_status: Validation status (PASSED, FAILED, WARNING)
        rule_id: Validation rule ID
        subject_type: Type of subject being validated
        details: Validation details
        task_id: Associated task ID
        passed: Whether validation passed
        **extra: Additional structured fields
    """
    ctx = get_correlation_context()

    extra_filtered = filter_sensitive_fields(extra)

    log_data = {
        "event": "validation",
        "validation_status": validation_status,
        "rule_id": rule_id,
        "subject_type": subject_type,
        "correlation_id": ctx.correlation_id,
        "trace_id": ctx.trace_id,
        "task_id": task_id or ctx.task_id,
        "passed": passed,
        **extra_filtered,
    }

    logger = get_structured_logger("eiw.validation", "validator")
    level = logger.logger.info if passed else logger.logger.warning
    level(f"Validation {validation_status}: {rule_id} - {details}", extra=log_data)


def log_span_completion(
    span_name: str,
    status: str,
    duration_ms: float,
    trace_id: str | None = None,
    span_id: str | None = None,
    task_id: str | None = None,
    error: Exception | None = None,
    **extra: Any,
) -> None:
    """Log span completion.

    Args:
        span_name: Name of the span
        status: Completion status (OK, ERROR)
        duration_ms: Span duration
        trace_id: Trace ID
        span_id: Span ID
        task_id: Associated task ID
        error: Exception if failed
        **extra: Additional structured fields
    """
    ctx = get_correlation_context()

    extra_filtered = filter_sensitive_fields(extra)

    log_data = {
        "event": "span_completed",
        "span_name": span_name,
        "correlation_id": ctx.correlation_id,
        "trace_id": trace_id or ctx.trace_id,
        "span_id": span_id or ctx.span_id,
        "task_id": task_id or ctx.task_id,
        "status": status,
        "duration_ms": duration_ms,
        "error_category": error.__class__.__name__ if error else None,
        **extra_filtered,
    }

    logger = get_structured_logger("eiw.trace", "tracer")
    if error:
        logger.error(f"Span {span_name} failed: {error}", extra=log_data)
    else:
        logger.info(f"Span {span_name} completed ({duration_ms:.2f}ms)", extra=log_data)


def log_audit_event(
    action: str,
    outcome: str,
    actor_id: str,
    resource_type: str,
    resource_id: str,
    policy_version: str,
    task_id: str | None = None,
    reason: str | None = None,
    **extra: Any,
) -> None:
    """Log an audit event.

    Args:
        action: Action being audited
        outcome: Outcome (ALLOWED, DENIED, ERROR)
        actor_id: User performing the action
        resource_type: Type of resource
        resource_id: ID of the resource
        policy_version: Policy version applied
        task_id: Associated task ID
        reason: Reason for the decision
        **extra: Additional structured fields
    """
    ctx = get_correlation_context()

    extra_filtered = filter_sensitive_fields(extra)

    log_data = {
        "event": "audit",
        "action": action,
        "outcome": outcome,
        "actor_id": actor_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "policy_version": policy_version,
        "correlation_id": ctx.correlation_id,
        "trace_id": ctx.trace_id,
        "task_id": task_id or ctx.task_id,
        "reason": reason,
        **extra_filtered,
    }

    logger = get_structured_logger("eiw.audit", "auditor")
    if outcome == "DENIED":
        logger.warning(f"Audit: {action} DENIED for {actor_id} on {resource_type}/{resource_id}", extra=log_data)
    elif outcome == "ERROR":
        logger.error(f"Audit: {action} ERROR for {actor_id} on {resource_type}/{resource_id}", extra=log_data)
    else:
        logger.info(f"Audit: {action} ALLOWED for {actor_id} on {resource_type}/{resource_id}", extra=log_data)
