"""Event Bus for Enterprise Data Agent.

Implements an internal event system for:
- Agent lifecycle events
- Tool execution events
- Analysis milestone events
- Error events
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of agent events."""

    # Agent lifecycle
    AGENT_STARTED = "agent_started"
    AGENT_STATE_CHANGED = "agent_state_changed"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"

    # Intent resolution
    INTENT_RESOLVED = "intent_resolved"
    INTENT_CONFUSED = "intent_confused"

    # Planning
    PLAN_CREATED = "plan_created"
    PLAN_STEP_STARTED = "plan_step_started"
    PLAN_STEP_COMPLETED = "plan_step_completed"

    # Tool execution
    TOOL_SELECTED = "tool_selected"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"

    # Hypothesis
    HYPOTHESIS_CREATED = "hypothesis_created"
    HYPOTHESIS_TESTED = "hypothesis_tested"
    HYPOTHESIS_SUPPORTED = "hypothesis_supported"
    HYPOTHESIS_REJECTED = "hypothesis_rejected"

    # Evidence
    EVIDENCE_GENERATED = "evidence_generated"
    EVIDENCE_VERIFIED = "evidence_verified"
    CLAIM_CREATED = "claim_created"
    CLAIM_VERIFIED = "claim_verified"

    # Analysis
    INSIGHT_GENERATED = "insight_generated"
    ANOMALY_DETECTED = "anomaly_detected"
    TREND_IDENTIFIED = "trend_identified"

    # Report
    REPORT_GENERATING = "report_generating"
    REPORT_GENERATED = "report_generated"


@dataclass
class AgentEvent:
    """An event in the agent system."""

    event_id: str
    event_type: EventType
    timestamp: datetime
    source: str  # component that emitted the event
    task_id: str | None
    data: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None


EventHandler = Callable[[AgentEvent], None]


class EventBus:
    """Internal event bus for agent events.

    This bus provides:
    - Event subscription with handlers
    - Event filtering
    - Async event processing
    - Event history
    """

    def __init__(self, max_history: int = 1000) -> None:
        """Initialize event bus.

        Args:
            max_history: Maximum number of events to keep in history
        """
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._all_handlers: list[EventHandler] = []
        self._history: list[AgentEvent] = []
        self._max_history = max_history

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """Subscribe to a specific event type.

        Args:
            event_type: Event type to subscribe to
            handler: Handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events.

        Args:
            handler: Handler function for all events
        """
        self._all_handlers.append(handler)

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """Unsubscribe from an event type.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type]
                if h != handler
            ]

    def unsubscribe_all(self, handler: EventHandler) -> None:
        """Unsubscribe from all events.

        Args:
            handler: Handler to remove
        """
        self._all_handlers = [h for h in self._all_handlers if h != handler]

    def emit(
        self,
        event_type: EventType,
        source: str,
        task_id: str | None = None,
        data: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> AgentEvent:
        """Emit an event.

        Args:
            event_type: Type of event
            source: Source component
            task_id: Related task ID
            data: Event data
            trace_id: Tracing ID

        Returns:
            The emitted event
        """
        event = AgentEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(UTC),
            source=source,
            task_id=task_id,
            data=data or {},
            trace_id=trace_id,
        )

        # Add to history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Call type-specific handlers
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                with contextlib.suppress(Exception):
                    handler(event)

        # Call all-handlers
        for handler in self._all_handlers:
            with contextlib.suppress(Exception):
                handler(event)

        return event

    def get_events(
        self,
        event_type: EventType | None = None,
        task_id: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[AgentEvent]:
        """Get events matching criteria.

        Args:
            event_type: Filter by event type
            task_id: Filter by task ID
            source: Filter by source
            limit: Maximum events to return

        Returns:
            Matching events
        """
        events = self._history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if task_id:
            events = [e for e in events if e.task_id == task_id]

        if source:
            events = [e for e in events if e.source == source]

        return events[-limit:]

    def get_task_timeline(self, task_id: str) -> list[AgentEvent]:
        """Get all events for a task in chronological order.

        Args:
            task_id: Task to get events for

        Returns:
            Events for the task
        """
        return [e for e in self._history if e.task_id == task_id]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# Convenience functions
def emit_event(
    event_type: EventType,
    source: str,
    task_id: str | None = None,
    data: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> AgentEvent:
    """Emit an event to the global event bus."""
    return get_event_bus().emit(event_type, source, task_id, data, trace_id)
