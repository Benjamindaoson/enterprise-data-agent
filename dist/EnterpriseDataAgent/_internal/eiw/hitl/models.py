"""Human-in-the-Loop (HitL) module.

This module provides:
- Human intervention types and decision models
- HitL service for managing human decisions
- SSE event streaming for real-time updates
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HumanDecisionType(str, Enum):
    """Types of decisions requiring human input."""

    METRIC_SELECTION = "metric_selection"
    TIME_RANGE_CONFIRMATION = "time_range_confirmation"
    HYPOTHESIS_APPROVAL = "hypothesis_approval"
    DIRECTION_SELECTION = "direction_selection"
    CLAIM_APPROVAL = "claim_approval"
    ALERT_REVIEW = "alert_review"
    CUSTOM = "custom"


class HumanDecisionStatus(str, Enum):
    """Status of a human decision request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class DecisionOption(BaseModel):
    """A single option in a decision request."""

    id: str = Field(description="Option identifier")
    label: str = Field(description="Human-readable label")
    description: str = Field(default="", description="Option description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HumanDecisionRequest(BaseModel):
    """Request for human decision."""

    task_id: str = Field(description="Associated task ID")
    decision_type: HumanDecisionType = Field(description="Type of decision needed")
    question: str = Field(description="Question to present to human")
    context: dict[str, Any] = Field(default_factory=dict, description="Decision context")
    options: list[DecisionOption] = Field(description="Available options")
    timeout_seconds: int = Field(default=300, description="Timeout in seconds")
    priority: int = Field(default=0, description="Priority level (higher = more urgent)")


class HumanDecisionResponse(BaseModel):
    """Response from human decision."""

    decision_id: str = Field(description="Decision request ID")
    selected_option_id: str | None = Field(default=None, description="Selected option ID")
    reasoning: str = Field(default="", description="Human's reasoning")
    status: HumanDecisionStatus = Field(description="Decision status")
    decided_by: str = Field(default="", description="User who made decision")
    decided_at: datetime = Field(default_factory=datetime.now)


class HitlEvent(BaseModel):
    """Event for SSE streaming."""

    event_type: str = Field(description="Event type")
    task_id: str = Field(description="Associated task ID")
    decision_id: str | None = Field(default=None)
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
