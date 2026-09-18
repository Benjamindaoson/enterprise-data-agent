"""OpenTelemetry instrumentation for Enterprise Data Agent.

Implements distributed tracing with OTLP export support.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SpanExporter
    from opentelemetry.sdk.resources import Resource


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class OTelConfig:
    """OpenTelemetry configuration."""

    service_name: str = "enterprise-data-agent"
    service_version: str = "1.0.0"
    otlp_endpoint: str | None = None  # None = no export, in-memory only
    environment: str = "development"
    enabled: bool = True


def get_otel_config() -> OTelConfig:
    """Get OTel configuration from environment."""
    return OTelConfig(
        service_name=os.getenv("OTEL_SERVICE_NAME", "enterprise-data-agent"),
        service_version=os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        environment=os.getenv("OTEL_ENVIRONMENT", "development"),
        enabled=os.getenv("OTEL_ENABLED", "true").lower() == "true",
    )


# =============================================================================
# Sensitive field filtering
# =============================================================================


# Fields that should NEVER be recorded in spans or logs
SENSITIVE_FIELDS: set[str] = {
    "password",
    "secret",
    "token",
    "api_key",
    "credential",
    "auth",
    "authorization",
    "private_key",
    "access_token",
    "refresh_token",
    "session_id",
    "ssn",
    "credit_card",
    "bank_account",
    "raw_sql",  # Could contain sensitive filters
    "user_input",  # Could contain sensitive data
    "chain_of_thought",
    "prompt",
    "system_prompt",
}


def filter_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive fields from data before recording."""
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Skip sensitive fields
        if any(sf in key_lower for sf in SENSITIVE_FIELDS):
            result[key] = "[REDACTED]"
            continue

        # Recursively filter nested dicts
        if isinstance(value, dict):
            result[key] = filter_sensitive_fields(value)
        elif isinstance(value, list):
            result[key] = [
                filter_sensitive_fields(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            result[key] = value

    return result


# =============================================================================
# Correlation ID
# =============================================================================


@dataclass
class CorrelationContext:
    """Context for correlating logs, traces, and events."""

    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str | None = None
    task_id: str | None = None
    span_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "span_id": self.span_id,
        }


# Thread-local correlation context
_correlation_context: CorrelationContext | None = None


def get_correlation_context() -> CorrelationContext:
    """Get current correlation context."""
    global _correlation_context
    if _correlation_context is None:
        _correlation_context = CorrelationContext()
    return _correlation_context


def set_correlation_context(
    correlation_id: str | None = None,
    trace_id: str | None = None,
    task_id: str | None = None,
    span_id: str | None = None,
) -> CorrelationContext:
    """Set correlation context for current execution."""
    global _correlation_context
    ctx = get_correlation_context()

    if correlation_id is not None:
        ctx.correlation_id = correlation_id
    if trace_id is not None:
        ctx.trace_id = trace_id
    if task_id is not None:
        ctx.task_id = task_id
    if span_id is not None:
        ctx.span_id = span_id

    return ctx


def clear_correlation_context() -> None:
    """Clear correlation context."""
    global _correlation_context
    _correlation_context = None


# =============================================================================
# Span attributes - data_agent.task hierarchy
# =============================================================================


# Required span attributes by span type
REQUIRED_SPAN_ATTRIBUTES: dict[str, list[str]] = {
    "data_agent.task": [
        "task_id",
        "domain_id",
        "correlation_id",
    ],
    "intent.resolve": [
        "task_id",
        "correlation_id",
        "input_length",
    ],
    "semantic.resolve": [
        "task_id",
        "correlation_id",
        "semantic_package_id",
        "semantic_package_version",
    ],
    "metric.retrieve": [
        "task_id",
        "metric_id",
        "metric_version",
    ],
    "schema.retrieve": [
        "task_id",
        "schema_id",
    ],
    "knowledge.retrieve": [
        "task_id",
        "query_type",
        "result_count",
    ],
    "plan.create": [
        "task_id",
        "step_count",
    ],
    "tool.select": [
        "task_id",
        "tool_name",
    ],
    "tool.execute": [
        "task_id",
        "tool_name",
        "correlation_id",
    ],
    "sql.generate": [
        "task_id",
        "query_lane",
    ],
    "sql.parse": [
        "task_id",
    ],
    "sql.policy_validate": [
        "task_id",
        "policy_version",
        "decision",
    ],
    "sql.execute": [
        "task_id",
        "tool_name",
        "row_count",
        "duration_ms",
    ],
    "validation": [
        "task_id",
        "validation_status",
    ],
    "hypothesis.update": [
        "task_id",
        "hypothesis_id",
        "new_state",
    ],
    "claim.synthesize": [
        "task_id",
        "claim_type",
    ],
    "report.generate": [
        "task_id",
        "artifact_type",
    ],
    "investigation.step": [
        "task_id",
        "step_ordinal",
        "tool_name",
    ],
}


# =============================================================================
# Tracer implementation
# =============================================================================


class EnterpriseTracer:
    """Enterprise-grade tracer with OTel integration.

    Provides structured tracing for the data_agent.task hierarchy.
    Supports both in-memory collection and OTLP export.
    """

    def __init__(self, config: OTelConfig | None = None) -> None:
        """Initialize tracer."""
        self.config = config or get_otel_config()
        self._provider: TracerProvider | None = None
        self._tracer: trace.Tracer | None = None
        self._exporter: SpanExporter | None = None
        self._spans: list[dict[str, Any]] = []  # In-memory span storage
        self._initialized = False

    def _initialize(self) -> None:
        """Initialize OTel SDK components."""
        if self._initialized or not self.config.enabled:
            return

        try:
            # Import OTel SDK components
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, InMemorySpanExporter
            from opentelemetry.sdk.resources import Resource

            # Create resource
            resource = Resource.create({
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
                "deployment.environment": self.config.environment,
            })

            # Create in-memory exporter (always enabled)
            self._exporter = InMemorySpanExporter()

            # Create provider with exporter
            self._provider = TracerProvider(resource=resource)
            self._provider.add_span_processor(BatchSpanProcessor(self._exporter))

            # Set global tracer provider
            trace.set_tracer_provider(self._provider)
            self._tracer = trace.get_tracer(__name__)

            self._initialized = True

        except ImportError:
            # OTel not installed - use simple in-memory fallback
            self._initialized = True

    @property
    def tracer(self) -> trace.Tracer | None:
        """Get OTel tracer."""
        self._initialize()
        return self._tracer

    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
        record_exception: bool = True,
    ) -> Any:
        """Start a new span.

        Args:
            name: Span name following data_agent.task hierarchy
            attributes: Span attributes (filtered for sensitive data)
            parent_span_id: Optional parent span ID
            record_exception: Whether to record exceptions

        Returns:
            Span context or in-memory span dict
        """
        self._initialize()

        # Filter sensitive fields
        safe_attributes = filter_sensitive_fields(attributes or {})

        # Add correlation context
        ctx = get_correlation_context()
        safe_attributes["correlation_id"] = ctx.correlation_id
        if ctx.task_id:
            safe_attributes["task_id"] = ctx.task_id
        if ctx.trace_id:
            safe_attributes["trace_id"] = ctx.trace_id

        if self.tracer:
            # Use real OTel tracer
            from opentelemetry import trace

            span = self.tracer.start_span(name, attributes=safe_attributes)
            return span

        # Fallback: in-memory span
        span_id = str(uuid4())[:16]
        span = {
            "span_id": span_id,
            "name": name,
            "trace_id": ctx.trace_id or str(uuid4()),
            "parent_span_id": parent_span_id,
            "attributes": safe_attributes,
            "start_time": datetime.now(UTC).isoformat(),
            "events": [],
            "status": "OK",
        }
        self._spans.append(span)
        set_correlation_context(span_id=span_id)
        return span

    def end_span(self, span: Any, status: str = "OK", error: Exception | None = None) -> None:
        """End a span."""
        if hasattr(span, "end"):
            # Real OTel span
            if error:
                span.record_exception(error)
                span.set_status("ERROR")
            span.end()
        elif isinstance(span, dict):
            # In-memory span
            span["end_time"] = datetime.now(UTC).isoformat()
            span["status"] = "ERROR" if error else status
            if error:
                span["error"] = str(error)

    def add_span_event(self, span: Any, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add event to span."""
        safe_attrs = filter_sensitive_fields(attributes or {})

        if hasattr(span, "add_event"):
            span.add_event(name, attributes=safe_attrs)
        elif isinstance(span, dict):
            span["events"].append({
                "name": name,
                "timestamp": datetime.now(UTC).isoformat(),
                "attributes": safe_attrs,
            })

    def set_span_attribute(self, span: Any, key: str, value: Any) -> None:
        """Set attribute on span."""
        if hasattr(span, "set_attribute"):
            span.set_attribute(key, value)
        elif isinstance(span, dict):
            safe_value = "[REDACTED]" if key.lower() in SENSITIVE_FIELDS else value
            span["attributes"][key] = safe_value

    def get_trace_spans(self, trace_id: str | None = None) -> list[dict[str, Any]]:
        """Get all spans for a trace."""
        if trace_id is None:
            ctx = get_correlation_context()
            trace_id = ctx.trace_id

        if self._exporter:
            # Get from exporter
            exported = self._exporter.get_finished_spans()
            if trace_id:
                return [s.to_dict() for s in exported if s.trace_id == trace_id]
            return [s.to_dict() for s in exported]

        # Get from in-memory storage
        if trace_id:
            return [s for s in self._spans if s.get("trace_id") == trace_id]
        return list(self._spans)

    def export_trace(self, trace_id: str | None = None) -> dict[str, Any]:
        """Export trace in OTLP-compatible format."""
        spans = self.get_trace_spans(trace_id)

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.config.service_name}},
                        {"key": "service.version", "value": {"stringValue": self.config.service_version}},
                    ]
                },
                "scopeSpans": [{
                    "spans": [
                        {
                            "span_id": s.get("span_id", ""),
                            "trace_id": s.get("trace_id", ""),
                            "parent_span_id": s.get("parent_span_id") or "",
                            "name": s.get("name", ""),
                            "kind": "INTERNAL",
                            "attributes": [
                                {"key": k, "value": {"stringValue": str(v)}}
                                for k, v in (s.get("attributes") or {}).items()
                            ],
                            "events": s.get("events", []),
                            "status": {"code": 1 if s.get("status") == "OK" else 2},
                        }
                        for s in spans
                    ]
                }]
            }]
        }


# Global tracer instance
_tracer: EnterpriseTracer | None = None


def get_tracer() -> EnterpriseTracer:
    """Get global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = EnterpriseTracer()
    return _tracer


def reset_tracer() -> None:
    """Reset tracer for testing."""
    global _tracer
    _tracer = None


# =============================================================================
# Context manager for spans
# =============================================================================


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    record_exception: bool = True,
):
    """Context manager for creating spans.

    Usage:
        with trace_span("intent.resolve", {"task_id": "123"}):
            result = resolve_intent(...)
    """
    tracer = get_tracer()
    span = tracer.start_span(name, attributes=attributes)

    try:
        yield span
    except Exception as e:
        tracer.end_span(span, status="ERROR", error=e)
        raise
    else:
        tracer.end_span(span, status="OK")


# =============================================================================
# Span decorators
# =============================================================================


def traced(
    span_name: str | None = None,
    attributes: dict[str, Any] | None = None,
):
    """Decorator for tracing functions.

    Usage:
        @traced("metric.retrieve")
        def retrieve_metric(metric_id: str) -> Metric:
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = span_name or func.__name__
            with trace_span(name, attributes):
                return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator
