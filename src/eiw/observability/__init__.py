"""Observability module for Enterprise Data Agent.

Provides:
- OpenTelemetry tracing
- Structured logging
- Event tracking
"""

from eiw.observability.events import (
    AgentEvent,
    EventBus,
    EventType,
    get_event_bus,
    emit_event,
)
from eiw.observability.otel import (
    OTelConfig,
    get_otel_config,
    EnterpriseTracer,
    get_tracer,
    reset_tracer,
    trace_span,
    traced,
    trace_span,
    CorrelationContext,
    get_correlation_context,
    set_correlation_context,
    clear_correlation_context,
    filter_sensitive_fields,
    SENSITIVE_FIELDS,
)
from eiw.observability.logging import (
    StructuredLogRecord,
    get_structured_logger,
    set_structured_logging_json,
    log_task_event,
    log_tool_execution,
    log_validation,
    log_span_completion,
    log_audit_event,
)

__all__ = [
    # Events
    "AgentEvent",
    "EventBus",
    "EventType",
    "get_event_bus",
    "emit_event",
    # OpenTelemetry
    "OTelConfig",
    "get_otel_config",
    "EnterpriseTracer",
    "get_tracer",
    "reset_tracer",
    "trace_span",
    "traced",
    "CorrelationContext",
    "get_correlation_context",
    "set_correlation_context",
    "clear_correlation_context",
    "filter_sensitive_fields",
    "SENSITIVE_FIELDS",
    # Logging
    "StructuredLogRecord",
    "get_structured_logger",
    "set_structured_logging_json",
    "log_task_event",
    "log_tool_execution",
    "log_validation",
    "log_span_completion",
    "log_audit_event",
]
