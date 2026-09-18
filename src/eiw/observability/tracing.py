"""OpenTelemetry Tracing for Enterprise Data Agent.

Implements distributed tracing for:
- Agent workflow spans
- Tool execution spans
- Query execution spans
- End-to-end request tracing
"""

from __future__ import annotations

import functools
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class SpanType(Enum):
    """Types of spans."""

    ROOT = "root"
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    TOOL = "tool"
    QUERY = "query"
    VALIDATION = "validation"
    SYNTHESIS = "synthesis"


@dataclass
class AgentSpan:
    """A tracing span for agent operations."""

    span_id: str
    trace_id: str
    parent_span_id: str | None
    span_type: SpanType
    name: str
    start_time: datetime
    end_time: datetime | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "OK"  # OK, ERROR
    error_message: str | None = None


class TracingManager:
    """Manages OpenTelemetry-style distributed tracing.

    This manager creates and manages spans for:
    - Agent workflow orchestration
    - Tool execution
    - Query processing
    - Evidence verification

    In production, this would integrate with:
    - OpenTelemetry SDK
    - Jaeger, Zipkin, or Tempo for visualization
    - Prometheus for metrics
    """

    def __init__(self, service_name: str = "enterprise-data-agent") -> None:
        """Initialize tracing manager.

        Args:
            service_name: Name of the service for tracing
        """
        self.service_name = service_name
        self._spans: dict[str, AgentSpan] = {}
        self._active_spans: dict[str, AgentSpan] = {}
        self._trace_count = 0

    def start_trace(self) -> str:
        """Start a new trace.

        Returns:
            Trace ID
        """
        self._trace_count += 1
        return f"trace-{uuid.uuid4().hex[:16]}"

    def start_span(
        self,
        trace_id: str,
        name: str,
        span_type: SpanType,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> AgentSpan:
        """Start a new span.

        Args:
            trace_id: Trace this span belongs to
            name: Name of the span
            span_type: Type of span
            parent_span_id: Parent span ID (for nesting)
            attributes: Initial span attributes

        Returns:
            Created span
        """
        span = AgentSpan(
            span_id=f"span-{uuid.uuid4().hex[:12]}",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            span_type=span_type,
            name=name,
            start_time=datetime.now(UTC),
            attributes=attributes or {},
        )

        self._spans[span.span_id] = span
        self._active_spans[span.span_id] = span

        return span

    def end_span(
        self,
        span_id: str,
        status: str = "OK",
        error_message: str | None = None,
    ) -> AgentSpan | None:
        """End a span.

        Args:
            span_id: Span to end
            status: Span status
            error_message: Error message if status is ERROR

        Returns:
            Ended span
        """
        span = self._active_spans.get(span_id)
        if not span:
            span = self._spans.get(span_id)

        if span:
            span.end_time = datetime.now(UTC)
            span.status = status
            span.error_message = error_message
            if span_id in self._active_spans:
                del self._active_spans[span_id]

        return span

    def add_span_event(
        self,
        span_id: str,
        event_name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Add an event to a span.

        Args:
            span_id: Span to add event to
            event_name: Name of the event
            attributes: Event attributes
        """
        span = self._spans.get(span_id)
        if span:
            span.events.append({
                "name": event_name,
                "timestamp": datetime.now(UTC).isoformat(),
                "attributes": attributes or {},
            })

    def set_span_attribute(
        self,
        span_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Set an attribute on a span.

        Args:
            span_id: Span to modify
            key: Attribute key
            value: Attribute value
        """
        span = self._spans.get(span_id)
        if span:
            span.attributes[key] = value

    def get_trace(self, trace_id: str) -> list[AgentSpan]:
        """Get all spans for a trace.

        Args:
            trace_id: Trace to retrieve

        Returns:
            List of spans in the trace
        """
        return [
            s for s in self._spans.values()
            if s.trace_id == trace_id
        ]

    def get_span_tree(self, trace_id: str) -> dict[str, Any]:
        """Get trace as a tree structure.

        Args:
            trace_id: Trace to visualize

        Returns:
            Tree representation of trace
        """
        spans = self.get_trace(trace_id)

        if not spans:
            return {"trace_id": trace_id, "spans": [], "tree": {}}

        # Find root span
        roots = [s for s in spans if s.parent_span_id is None]
        root = roots[0] if roots else spans[0]

        def build_tree(span_id: str) -> dict[str, Any]:
            span = next((s for s in spans if s.span_id == span_id), None)
            if not span:
                return {}

            children = [s for s in spans if s.parent_span_id == span_id]

            return {
                "span_id": span.span_id,
                "name": span.name,
                "type": span.span_type.value,
                "status": span.status,
                "duration_ms": (
                    (span.end_time - span.start_time).total_seconds() * 1000
                    if span.end_time else None
                ),
                "attributes": span.attributes,
                "children": [build_tree(c.span_id) for c in children],
            }

        return {
            "trace_id": trace_id,
            "root_span": root.span_id,
            "tree": build_tree(root.span_id),
            "total_spans": len(spans),
        }

    def export_trace(self, trace_id: str) -> dict[str, Any]:
        """Export trace in OpenTelemetry-compatible format.

        Args:
            trace_id: Trace to export

        Returns:
            OTLP-compatible trace dict
        """
        spans = self.get_trace(trace_id)

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.service_name}}
                    ]
                },
                "scopeSpans": [{
                    "spans": [
                        {
                            "span_id": s.span_id,
                            "trace_id": s.trace_id,
                            "parent_span_id": s.parent_span_id or "",
                            "name": s.name,
                            "kind": s.span_type.value.upper(),
                            "start_time_unix_nano": int(s.start_time.timestamp() * 1e9),
                            "end_time_unix_nano": (
                                int(s.end_time.timestamp() * 1e9) if s.end_time else 0
                            ),
                            "attributes": [
                                {"key": k, "value": {"stringValue": str(v)}}
                                for k, v in s.attributes.items()
                            ],
                            "events": [
                                {
                                    "name": e["name"],
                                    "timestamp_unix_nano": int(
                                        datetime.fromisoformat(e["timestamp"]).timestamp() * 1e9
                                    ),
                                }
                                for e in s.events
                            ],
                            "status": {"code": 1 if s.status == "OK" else 2},
                        }
                        for s in spans
                    ]
                }]
            }]
        }


# Global tracing manager instance
_tracing_manager: TracingManager | None = None


def get_tracing_manager() -> TracingManager:
    """Get the global tracing manager instance."""
    global _tracing_manager
    if _tracing_manager is None:
        _tracing_manager = TracingManager()
    return _tracing_manager


@contextmanager
def create_span(
    name: str,
    span_type: SpanType,
    trace_id: str | None = None,
    parent_span_id: str | None = None,
    attributes: dict[str, Any] | None = None,
):
    """Context manager for creating and ending spans.

    Args:
        name: Span name
        span_type: Type of span
        trace_id: Trace ID (auto-generated if not provided)
        parent_span_id: Parent span ID
        attributes: Initial attributes

    Yields:
        The created span
    """
    manager = get_tracing_manager()

    if trace_id is None:
        trace_id = manager.start_trace()

    span = manager.start_span(
        trace_id=trace_id,
        name=name,
        span_type=span_type,
        parent_span_id=parent_span_id,
        attributes=attributes,
    )

    try:
        yield span
    except Exception as e:
        manager.end_span(span.span_id, status="ERROR", error_message=str(e))
        raise
    else:
        manager.end_span(span.span_id)


def trace_async(
    span_name: str | None = None,
    span_type: SpanType = SpanType.TOOL,
):
    """Decorator for tracing async functions.

    Args:
        span_name: Custom span name (defaults to function name)
        span_type: Type of span
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = span_name or func.__name__

            with create_span(name, span_type) as span:
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.status = "ERROR"
                    span.error_message = str(e)
                    raise

        return wrapper
    return decorator


def trace_sync(
    span_name: str | None = None,
    span_type: SpanType = SpanType.TOOL,
):
    """Decorator for tracing sync functions.

    Args:
        span_name: Custom span name (defaults to function name)
        span_type: Type of span
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = span_name or func.__name__

            with create_span(name, span_type) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.status = "ERROR"
                    span.error_message = str(e)
                    raise

        return wrapper
    return decorator
