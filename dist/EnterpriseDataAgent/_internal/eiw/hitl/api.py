"""HitL API Routes.

Provides FastAPI routes for human-in-the-loop interactions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import EventSourceResponse
from pydantic import BaseModel, Field

from eiw.hitl import (
    DecisionOption,
    HitlEvent,
    HumanDecisionRequest,
    HumanDecisionResponse,
    HumanDecisionStatus,
    HumanDecisionType,
    get_hitl_service,
)

# Request/Response models
class CreateDecisionRequest(BaseModel):
    """Request to create a human decision."""

    task_id: str = Field(description="Task ID")
    decision_type: HumanDecisionType = Field(description="Type of decision")
    question: str = Field(description="Question to ask")
    options: list[dict[str, Any]] = Field(description="Available options")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    timeout_seconds: int = Field(default=300, description="Timeout in seconds")
    priority: int = Field(default=0, description="Priority")


class SubmitDecisionRequest(BaseModel):
    """Request to submit a decision."""

    selected_option_id: str = Field(description="Selected option ID")
    reasoning: str = Field(default="", description="Reasoning")
    decided_by: str = Field(default="", description="User who decided")


class DecisionStatusResponse(BaseModel):
    """Response with decision status."""

    decision_id: str
    status: HumanDecisionStatus
    question: str | None = None
    options: list[dict] = []
    timeout_seconds: int


# Router
router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])


@router.post("/decisions", response_model=dict)
async def create_decision(request: CreateDecisionRequest):
    """Create a new human decision request.

    Returns decision ID and waits for response.
    """
    hitl = get_hitl_service()

    # Convert options
    options = [
        DecisionOption(
            id=opt.get("id", f"opt_{i}"),
            label=opt.get("label", ""),
            description=opt.get("description", ""),
        )
        for i, opt in enumerate(request.options)
    ]

    # Create request
    hitl_request = HumanDecisionRequest(
        task_id=request.task_id,
        decision_type=request.decision_type,
        question=request.question,
        options=options,
        context=request.context,
        timeout_seconds=request.timeout_seconds,
        priority=request.priority,
    )

    decision_id = await hitl.create_decision_request(hitl_request)

    return {
        "decision_id": decision_id,
        "status": "pending",
        "timeout_seconds": request.timeout_seconds,
    }


@router.post("/decisions/{decision_id}/respond")
async def submit_decision(
    decision_id: str,
    request: SubmitDecisionRequest,
):
    """Submit a decision response."""
    hitl = get_hitl_service()

    # Try to submit as approval
    response = await hitl.submit_decision(
        decision_id=decision_id,
        selected_option_id=request.selected_option_id,
        reasoning=request.reasoning,
        decided_by=request.decided_by,
    )

    if response is None:
        # Try reject
        response = await hitl.reject_decision(
            decision_id=decision_id,
            reasoning=request.reasoning,
            decided_by=request.decided_by,
        )

    if response is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    return response.model_dump()


@router.get("/decisions/{decision_id}", response_model=DecisionStatusResponse)
async def get_decision_status(decision_id: str):
    """Get decision status."""
    hitl = get_hitl_service()

    status = hitl.get_decision_status(decision_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    response = hitl.get_decision_response(decision_id)
    request = hitl._decision_requests.get(decision_id)

    return DecisionStatusResponse(
        decision_id=decision_id,
        status=status,
        question=request.question if request else None,
        options=[o.model_dump() for o in request.options] if request else [],
        timeout_seconds=request.timeout_seconds if request else 300,
    )


@router.get("/decisions/{decision_id}/response")
async def get_decision_response(decision_id: str):
    """Get decision response if available."""
    hitl = get_hitl_service()

    response = hitl.get_decision_response(decision_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Response not yet available")

    return response.model_dump()


@router.get("/tasks/{task_id}/decisions")
async def get_task_decisions(task_id: str):
    """Get all decisions for a task."""
    hitl = get_hitl_service()

    pending = hitl.get_pending_decisions(task_id)

    return {
        "task_id": task_id,
        "pending_count": len(pending),
        "decisions": [
            {
                "decision_id": did,
                "status": hitl.get_decision_status(did).value if hitl.get_decision_status(did) else "unknown",
            }
            for did in hitl._task_decisions.get(task_id, [])
        ],
    }


@router.get("/tasks/{task_id}/events")
async def stream_task_events(task_id: str):
    """Stream events for a task via SSE.

    Returns Server-Sent Events stream.
    """
    hitl = get_hitl_service()
    queue = await hitl.subscribe(task_id)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield f"data: {event.model_dump_json()}\n\n"
        except Exception:
            pass
        finally:
            await hitl.unsubscribe(task_id, queue)

    return EventSourceResponse(event_generator())
