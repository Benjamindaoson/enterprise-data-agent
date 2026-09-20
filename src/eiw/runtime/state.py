"""Runtime state management for Enterprise Data Agent.

Handles durable task state separate from model context:
- Task state persistence
- Checkpoint management
- Recovery mechanisms
- Budget tracking
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class TaskState:
    """Persistent state for an analysis task."""

    task_id: str
    state_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    question: str = ""
    state: str = "CREATED"
    events: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    max_steps: int = 10
    query_count: int = 0
    tool_calls: int = 0
    runtime_seconds: float = 0.0
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "state_id": self.state_id,
            "version": self.version,
            "question": self.question,
            "state": self.state,
            "events": self.events,
            "observations": self.observations,
            "claims": self.claims,
            "evidence": self.evidence,
            "hypotheses": self.hypotheses,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "query_count": self.query_count,
            "tool_calls": self.tool_calls,
            "runtime_seconds": self.runtime_seconds,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskState":
        """Deserialize from dictionary."""
        return cls(
            task_id=data["task_id"],
            state_id=data.get("state_id", str(uuid4())),
            version=data.get("version", 1),
            question=data.get("question", ""),
            state=data.get("state", "CREATED"),
            events=data.get("events", []),
            observations=data.get("observations", []),
            claims=data.get("claims", []),
            evidence=data.get("evidence", []),
            hypotheses=data.get("hypotheses", []),
            current_step=data.get("current_step", 0),
            max_steps=data.get("max_steps", 10),
            query_count=data.get("query_count", 0),
            tool_calls=data.get("tool_calls", 0),
            runtime_seconds=data.get("runtime_seconds", 0.0),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(UTC),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(UTC),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )


@dataclass
class Checkpoint:
    """A checkpoint for resumable task execution."""

    checkpoint_id: str
    task_id: str
    version: int
    state: dict[str, Any]
    step_index: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    storage_uri: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "version": self.version,
            "step_index": self.step_index,
            "created_at": self.created_at.isoformat(),
            "storage_uri": self.storage_uri,
        }


class StateManager:
    """Manages durable task state and checkpoints.

    This implements the runtime separation of durable task state
    from model context, enabling:
    - Checkpoint and resume
    - Recovery from failures
    - Budget tracking
    - Trace and replay
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize state manager.

        Args:
            storage_path: Path for state persistence. If None, uses in-memory storage.
        """
        self._storage_path = storage_path
        self._states: dict[str, TaskState] = {}
        self._checkpoints: dict[str, list[Checkpoint]] = {}

        if storage_path:
            self._load_states()

    def create_state(self, task_id: str, question: str, max_steps: int = 10) -> TaskState:
        """Create a new task state."""
        state = TaskState(
            task_id=task_id,
            question=question,
            max_steps=max_steps,
        )
        self._states[task_id] = state
        self._save_state(state)
        return state

    def get_state(self, task_id: str) -> TaskState | None:
        """Get task state by ID."""
        if task_id not in self._states:
            # Try to load from storage
            if self._storage_path:
                state_file = self._storage_path / f"{task_id}.json"
                if state_file.exists():
                    data = json.loads(state_file.read_text())
                    self._states[task_id] = TaskState.from_dict(data)
        return self._states.get(task_id)

    def update_state(self, state: TaskState) -> TaskState:
        """Update task state and persist."""
        state.version += 1
        state.updated_at = datetime.now(UTC)
        self._states[state.task_id] = state
        self._save_state(state)
        return state

    def add_observation(self, task_id: str, observation: dict[str, Any]) -> None:
        """Add an observation to task state."""
        state = self.get_state(task_id)
        if state:
            state.observations.append(observation)
            self.update_state(state)

    def add_claim(self, task_id: str, claim: dict[str, Any]) -> None:
        """Add a claim to task state."""
        state = self.get_state(task_id)
        if state:
            state.claims.append(claim)
            self.update_state(state)

    def add_evidence(self, task_id: str, evidence: dict[str, Any]) -> None:
        """Add evidence to task state."""
        state = self.get_state(task_id)
        if state:
            state.evidence.append(evidence)
            self.update_state(state)

    def add_event(self, task_id: str, event_type: str, message: str, **kwargs: Any) -> None:
        """Add an event to task state."""
        state = self.get_state(task_id)
        if state:
            event = {
                "event_id": str(uuid4()),
                "event_type": event_type,
                "message": message,
                "timestamp": datetime.now(UTC).isoformat(),
                **kwargs,
            }
            state.events.append(event)
            self.update_state(state)

    def increment_step(self, task_id: str) -> int:
        """Increment current step and return new value."""
        state = self.get_state(task_id)
        if state:
            state.current_step += 1
            self.update_state(state)
            return state.current_step
        return 0

    def increment_tool_calls(self, task_id: str) -> int:
        """Increment tool call count."""
        state = self.get_state(task_id)
        if state:
            state.tool_calls += 1
            self.update_state(state)
            return state.tool_calls
        return 0

    def record_runtime(self, task_id: str, seconds: float) -> None:
        """Record runtime in seconds."""
        state = self.get_state(task_id)
        if state:
            state.runtime_seconds = seconds
            self.update_state(state)

    def is_budget_exceeded(self, task_id: str) -> bool:
        """Check if task has exceeded its budget."""
        state = self.get_state(task_id)
        if not state:
            return False

        # Check each budget dimension
        if state.current_step >= state.max_steps:
            return True

        if state.tool_calls >= (state.max_steps * 2):  # Rough estimate
            return True

        if state.runtime_seconds >= 300:  # 5 minutes max
            return True

        return False

    def create_checkpoint(self, task_id: str) -> Checkpoint:
        """Create a checkpoint for the current state."""
        state = self.get_state(task_id)
        if not state:
            raise ValueError(f"State not found for task: {task_id}")

        checkpoint_id = str(uuid4())
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            version=state.version,
            state=state.to_dict(),
            step_index=state.current_step,
            storage_uri=f"checkpoints/{task_id}/{checkpoint_id}.json",
        )

        # Store checkpoint
        if task_id not in self._checkpoints:
            self._checkpoints[task_id] = []
        self._checkpoints[task_id].append(checkpoint)

        # Persist checkpoint
        if self._storage_path:
            cp_dir = self._storage_path / "checkpoints" / task_id
            cp_dir.mkdir(parents=True, exist_ok=True)
            cp_file = cp_dir / f"{checkpoint_id}.json"
            cp_file.write_text(json.dumps(checkpoint.to_dict(), indent=2))

        return checkpoint

    def get_latest_checkpoint(self, task_id: str) -> Checkpoint | None:
        """Get the most recent checkpoint for a task."""
        checkpoints = self._checkpoints.get(task_id, [])
        return checkpoints[-1] if checkpoints else None

    def restore_from_checkpoint(self, checkpoint: Checkpoint) -> TaskState:
        """Restore task state from a checkpoint."""
        state = TaskState.from_dict(checkpoint.state)
        self._states[state.task_id] = state
        self.update_state(state)
        return state

    def _save_state(self, state: TaskState) -> None:
        """Persist state to storage."""
        if self._storage_path:
            state_file = self._storage_path / f"{state.task_id}.json"
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps(state.to_dict(), indent=2, default=str))

    def _load_states(self) -> None:
        """Load states from storage on startup."""
        if not self._storage_path or not self._storage_path.exists():
            return

        for state_file in self._storage_path.glob("*.json"):
            if state_file.stem == "index":  # Skip index file
                continue
            try:
                data = json.loads(state_file.read_text())
                state = TaskState.from_dict(data)
                self._states[state.task_id] = state
            except (json.JSONDecodeError, KeyError):
                continue

    def get_trace(self, task_id: str) -> dict[str, Any]:
        """Get a complete trace for a task."""
        state = self.get_state(task_id)
        if not state:
            return {}

        return {
            "task_id": task_id,
            "events": state.events,
            "observations": state.observations,
            "claims": state.claims,
            "evidence": state.evidence,
            "checkpoints": [
                cp.to_dict() for cp in self._checkpoints.get(task_id, [])
            ],
            "metrics": {
                "total_steps": state.current_step,
                "total_observations": len(state.observations),
                "total_claims": len(state.claims),
                "total_evidence": len(state.evidence),
                "runtime_seconds": state.runtime_seconds,
                "tool_calls": state.tool_calls,
            },
        }
