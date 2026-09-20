"""Human-in-the-Loop Service.

This service manages human intervention in agent workflows:
- Creating decision requests
- Tracking decision status
- Broadcasting events via SSE
- Handling timeouts
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable

from eiw.hitl.models import (
    DecisionOption,
    HitlEvent,
    HumanDecisionRequest,
    HumanDecisionResponse,
    HumanDecisionStatus,
    HumanDecisionType,
)
from eiw.observability.logging import get_structured_logger

logger = get_structured_logger(__name__, "hitl_service")


class HitlService:
    """Service for managing human-in-the-loop decisions."""

    def __init__(self):
        self._decision_requests: dict[str, HumanDecisionRequest] = {}
        self._decision_responses: dict[str, HumanDecisionResponse] = {}
        self._task_decisions: dict[str, list[str]] = defaultdict(list)
        self._event_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._timeout_tasks: dict[str, asyncio.Task] = {}

    async def create_decision_request(
        self,
        request: HumanDecisionRequest,
    ) -> str:
        """Create a new human decision request.

        Args:
            request: Decision request details

        Returns:
            Decision ID
        """
        decision_id = str(uuid.uuid4())[:8]
        request.task_id = request.task_id  # Ensure task_id is set
        self._decision_requests[decision_id] = request
        self._task_decisions[request.task_id].append(decision_id)

        # Set up timeout handler
        self._timeout_tasks[decision_id] = asyncio.create_task(
            self._handle_timeout(decision_id, request.timeout_seconds)
        )

        # Broadcast event
        await self._broadcast_event(HitlEvent(
            event_type="decision_requested",
            task_id=request.task_id,
            decision_id=decision_id,
            data={
                "decision_type": request.decision_type.value,
                "question": request.question,
                "options": [o.model_dump() for o in request.options],
                "timeout_seconds": request.timeout_seconds,
            },
        ))

        logger.info(
            f"Created decision request {decision_id}",
            extra={
                "task_id": request.task_id,
                "decision_type": request.decision_type.value,
                "timeout_seconds": request.timeout_seconds,
            },
        )

        return decision_id

    async def submit_decision(
        self,
        decision_id: str,
        selected_option_id: str,
        reasoning: str = "",
        decided_by: str = "",
    ) -> HumanDecisionResponse | None:
        """Submit a human decision.

        Args:
            decision_id: Decision request ID
            selected_option_id: Selected option ID
            reasoning: Human's reasoning
            decided_by: User who made the decision

        Returns:
            Decision response or None if not found
        """
        request = self._decision_requests.get(decision_id)
        if not request:
            logger.warning(f"Decision request not found: {decision_id}")
            return None

        # Cancel timeout task
        if decision_id in self._timeout_tasks:
            self._timeout_tasks[decision_id].cancel()
            del self._timeout_tasks[decision_id]

        response = HumanDecisionResponse(
            decision_id=decision_id,
            selected_option_id=selected_option_id,
            reasoning=reasoning,
            status=HumanDecisionStatus.APPROVED,
            decided_by=decided_by,
            decided_at=datetime.now(),
        )
        self._decision_responses[decision_id] = response

        # Broadcast event
        await self._broadcast_event(HitlEvent(
            event_type="decision_submitted",
            task_id=request.task_id,
            decision_id=decision_id,
            data={
                "selected_option_id": selected_option_id,
                "reasoning": reasoning,
                "decided_by": decided_by,
            },
        ))

        logger.info(
            f"Decision submitted for {decision_id}",
            extra={
                "task_id": request.task_id,
                "selected_option_id": selected_option_id,
                "decided_by": decided_by,
            },
        )

        return response

    async def reject_decision(
        self,
        decision_id: str,
        reasoning: str = "",
        decided_by: str = "",
    ) -> HumanDecisionResponse | None:
        """Reject a decision request.

        Args:
            decision_id: Decision request ID
            reasoning: Rejection reason
            decided_by: User who rejected

        Returns:
            Decision response or None if not found
        """
        request = self._decision_requests.get(decision_id)
        if not request:
            return None

        if decision_id in self._timeout_tasks:
            self._timeout_tasks[decision_id].cancel()
            del self._timeout_tasks[decision_id]

        response = HumanDecisionResponse(
            decision_id=decision_id,
            selected_option_id=None,
            reasoning=reasoning,
            status=HumanDecisionStatus.REJECTED,
            decided_by=decided_by,
            decided_at=datetime.now(),
        )
        self._decision_responses[decision_id] = response

        await self._broadcast_event(HitlEvent(
            event_type="decision_rejected",
            task_id=request.task_id,
            decision_id=decision_id,
            data={"reasoning": reasoning, "decided_by": decided_by},
        ))

        return response

    def get_decision_status(self, decision_id: str) -> HumanDecisionStatus | None:
        """Get current status of a decision.

        Args:
            decision_id: Decision request ID

        Returns:
            Status or None if not found
        """
        if decision_id in self._decision_responses:
            return self._decision_responses[decision_id].status
        if decision_id in self._decision_requests:
            return HumanDecisionStatus.PENDING
        return None

    def get_decision_response(self, decision_id: str) -> HumanDecisionResponse | None:
        """Get the response for a decision.

        Args:
            decision_id: Decision request ID

        Returns:
            Response or None
        """
        return self._decision_responses.get(decision_id)

    def get_pending_decisions(self, task_id: str) -> list[HumanDecisionRequest]:
        """Get all pending decisions for a task.

        Args:
            task_id: Task ID

        Returns:
            List of pending decision requests
        """
        decision_ids = self._task_decisions.get(task_id, [])
        return [
            self._decision_requests[did]
            for did in decision_ids
            if did in self._decision_requests and did not in self._decision_responses
        ]

    async def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe to events for a task.

        Args:
            task_id: Task ID to subscribe to

        Returns:
            Queue for receiving events
        """
        queue = asyncio.Queue()
        self._event_subscribers[task_id].append(queue)
        return queue

    async def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from task events.

        Args:
            task_id: Task ID
            queue: Queue to remove
        """
        if task_id in self._event_subscribers:
            with __import__('contextlib').suppress(ValueError):
                self._event_subscribers[task_id].remove(queue)

    async def _broadcast_event(self, event: HitlEvent) -> None:
        """Broadcast event to all subscribers.

        Args:
            event: Event to broadcast
        """
        if event.task_id in self._event_subscribers:
            for queue in self._event_subscribers[event.task_id]:
                await queue.put(event)

    async def _handle_timeout(self, decision_id: str, timeout_seconds: int) -> None:
        """Handle decision timeout.

        Args:
            decision_id: Decision request ID
            timeout_seconds: Timeout duration
        """
        try:
            await asyncio.sleep(timeout_seconds)

            # Check if still pending
            if decision_id in self._decision_responses:
                return  # Already decided

            request = self._decision_requests.get(decision_id)
            if not request:
                return

            # Mark as timeout
            response = HumanDecisionResponse(
                decision_id=decision_id,
                selected_option_id=None,
                reasoning="Decision timed out",
                status=HumanDecisionStatus.TIMEOUT,
                decided_by="",
                decided_at=datetime.now(),
            )
            self._decision_responses[decision_id] = response

            await self._broadcast_event(HitlEvent(
                event_type="decision_timeout",
                task_id=request.task_id,
                decision_id=decision_id,
                data={},
            ))

            logger.warning(
                f"Decision {decision_id} timed out",
                extra={"task_id": request.task_id},
            )

        except asyncio.CancelledError:
            pass  # Normal cancellation


# Global HitL service instance
_hitl_service: HitlService | None = None


def get_hitl_service() -> HitlService:
    """Get or create the global HitL service instance."""
    global _hitl_service
    if _hitl_service is None:
        _hitl_service = HitlService()
    return _hitl_service
