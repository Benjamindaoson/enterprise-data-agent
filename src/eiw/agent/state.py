"""Durable State Management - Checkpoint and Resume.

This module provides:
- Persistent state storage
- Checkpoint creation
- State recovery
- Task persistence
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "state")


# =============================================================================
# State Storage Types
# =============================================================================


class StateStorageType(str, Enum):
    """Storage backend types."""

    MEMORY = "memory"
    FILE = "file"
    DATABASE = "database"


class CheckpointMetadata(BaseModel):
    """Metadata for a checkpoint."""

    model_config = ConfigDict(extra="forbid")

    checkpoint_id: str = Field(description="Unique checkpoint ID")
    task_id: str = Field(description="Associated task ID")
    created_at: datetime = Field(default_factory=datetime.now)
    state_type: str = Field(description="Type of state stored")
    size_bytes: int = Field(default=0, description="Size of checkpoint")
    version: str = Field(default="1.0", description="Checkpoint format version")
    parent_checkpoint_id: str | None = Field(default=None, description="Parent checkpoint for lineage")


@dataclass
class Checkpoint:
    """A checkpoint of agent state."""

    metadata: CheckpointMetadata
    state: dict[str, Any]
    full_checkpoint: bool = True  # True = full state, False = delta

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.model_dump(),
            "state": self.state,
            "full_checkpoint": self.full_checkpoint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        return cls(
            metadata=CheckpointMetadata(**data["metadata"]),
            state=data["state"],
            full_checkpoint=data.get("full_checkpoint", True),
        )


# =============================================================================
# State Manager
# =============================================================================


class DurableStateManager:
    """Manages durable state with checkpoint/resume capability.

    This manager:
    - Stores agent state
    - Creates checkpoints
    - Recovers from checkpoints
    - Manages checkpoint lifecycle
    """

    def __init__(
        self,
        storage_type: StateStorageType = StateStorageType.FILE,
        storage_path: str | None = None,
        max_checkpoints: int = 10,
    ):
        """Initialize state manager.

        Args:
            storage_type: Where to store state
            storage_path: Path for file storage
            max_checkpoints: Maximum checkpoints to keep per task
        """
        self._storage_type = storage_type
        self._storage_path = storage_path or self._get_default_path()
        self._max_checkpoints = max_checkpoints
        self._memory_store: dict[str, dict[str, Any]] = {}
        self._checkpoints: dict[str, list[CheckpointMetadata]] = {}

        # Ensure storage path exists
        if storage_type == StateStorageType.FILE:
            Path(self._storage_path).mkdir(parents=True, exist_ok=True)

    def _get_default_path(self) -> str:
        """Get default storage path."""
        return os.path.join(os.getcwd(), ".eiw", "state")

    def save_state(
        self,
        task_id: str,
        state: dict[str, Any],
        create_checkpoint: bool = True,
    ) -> str:
        """Save agent state.

        Args:
            task_id: Task identifier
            state: State to save
            create_checkpoint: Whether to create a checkpoint

        Returns:
            Checkpoint ID if created
        """
        checkpoint_id = ""

        if create_checkpoint:
            checkpoint_id = self._create_checkpoint(task_id, state)

        # Always update current state
        if self._storage_type == StateStorageType.MEMORY:
            self._memory_store[task_id] = state
        elif self._storage_type == StateStorageType.FILE:
            self._save_to_file(task_id, state)

        logger.info(f"Saved state for task {task_id}", extra={"checkpoint_id": checkpoint_id})
        return checkpoint_id

    def _create_checkpoint(
        self,
        task_id: str,
        state: dict[str, Any],
    ) -> str:
        """Create a checkpoint.

        Args:
            task_id: Task identifier
            state: State to checkpoint

        Returns:
            Checkpoint ID
        """
        import uuid

        checkpoint_id = f"ckpt_{task_id}_{uuid.uuid4().hex[:8]}"

        # Get parent
        parent = None
        if task_id in self._checkpoints and self._checkpoints[task_id]:
            parent = self._checkpoints[task_id][-1].checkpoint_id

        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            state_type="agent_state",
            size_bytes=len(json.dumps(state)),
            parent_checkpoint_id=parent,
        )

        checkpoint = Checkpoint(metadata=metadata, state=state)

        # Store checkpoint
        if self._storage_type == StateStorageType.MEMORY:
            self._checkpoints.setdefault(task_id, []).append(metadata)
        elif self._storage_type == StateStorageType.FILE:
            self._save_checkpoint(checkpoint)

        # Trim old checkpoints
        self._trim_checkpoints(task_id)

        return checkpoint_id

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to file.

        Args:
            checkpoint: Checkpoint to save
        """
        task_path = Path(self._storage_path) / checkpoint.metadata.task_id
        task_path.mkdir(parents=True, exist_ok=True)

        checkpoint_file = task_path / f"{checkpoint.metadata.checkpoint_id}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

        # Update index
        self._checkpoints.setdefault(checkpoint.metadata.task_id, []).append(checkpoint.metadata)

    def _save_to_file(self, task_id: str, state: dict[str, Any]) -> None:
        """Save current state to file.

        Args:
            task_id: Task identifier
            state: State to save
        """
        task_path = Path(self._storage_path) / task_id
        task_path.mkdir(parents=True, exist_ok=True)

        state_file = task_path / "current.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self, task_id: str) -> dict[str, Any] | None:
        """Load current state for a task.

        Args:
            task_id: Task identifier

        Returns:
            State if found, None otherwise
        """
        if self._storage_type == StateStorageType.MEMORY:
            return self._memory_store.get(task_id)
        elif self._storage_type == StateStorageType.FILE:
            return self._load_from_file(task_id)
        return None

    def _load_from_file(self, task_id: str) -> dict[str, Any] | None:
        """Load state from file.

        Args:
            task_id: Task identifier

        Returns:
            State if found
        """
        state_file = Path(self._storage_path) / task_id / "current.json"
        if state_file.exists():
            with open(state_file, encoding="utf-8") as f:
                return json.load(f)
        return None

    def load_checkpoint(self, checkpoint_id: str, task_id: str) -> dict[str, Any] | None:
        """Load a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier
            task_id: Task identifier

        Returns:
            Checkpoint state if found
        """
        if self._storage_type == StateStorageType.FILE:
            checkpoint_file = Path(self._storage_path) / task_id / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                with open(checkpoint_file, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("state")
        return None

    def get_latest_checkpoint(self, task_id: str) -> str | None:
        """Get the latest checkpoint ID for a task.

        Args:
            task_id: Task identifier

        Returns:
            Latest checkpoint ID
        """
        if task_id in self._checkpoints and self._checkpoints[task_id]:
            return self._checkpoints[task_id][-1].checkpoint_id
        return None

    def get_checkpoint_history(self, task_id: str) -> list[CheckpointMetadata]:
        """Get checkpoint history for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of checkpoint metadata
        """
        return self._checkpoints.get(task_id, [])

    def _trim_checkpoints(self, task_id: str) -> None:
        """Trim old checkpoints, keeping most recent.

        Args:
            task_id: Task identifier
        """
        if task_id not in self._checkpoints:
            return

        checkpoints = self._checkpoints[task_id]
        if len(checkpoints) > self._max_checkpoints:
            # Remove oldest
            to_remove = checkpoints[:-self._max_checkpoints]
            self._checkpoints[task_id] = checkpoints[-self._max_checkpoints:]

            # Delete files
            if self._storage_type == StateStorageType.FILE:
                for ckpt in to_remove:
                    ckpt_file = Path(self._storage_path) / task_id / f"{ckpt.checkpoint_id}.json"
                    if ckpt_file.exists():
                        ckpt_file.unlink()

    def delete_task_state(self, task_id: str) -> None:
        """Delete all state for a task.

        Args:
            task_id: Task identifier
        """
        # Remove from memory
        self._memory_store.pop(task_id, None)
        self._checkpoints.pop(task_id, None)

        # Remove files
        if self._storage_type == StateStorageType.FILE:
            import shutil
            task_path = Path(self._storage_path) / task_id
            if task_path.exists():
                shutil.rmtree(task_path)

    def list_tasks(self) -> list[str]:
        """List all tasks with saved state.

        Returns:
            List of task IDs
        """
        if self._storage_type == StateStorageType.MEMORY:
            return list(self._memory_store.keys())
        elif self._storage_type == StateStorageType.FILE:
            return [p.name for p in Path(self._storage_path).iterdir() if p.is_dir()]
        return []


# =============================================================================
# Task State Builder
# =============================================================================


class TaskStateBuilder:
    """Helper to build and update task state."""

    def __init__(self, state_manager: DurableStateManager):
        """Initialize builder.

        Args:
            state_manager: State manager to use
        """
        self._state_manager = state_manager
        self._state: dict[str, Any] = {}

    def set_task_id(self, task_id: str) -> "TaskStateBuilder":
        """Set task ID."""
        self._state["task_id"] = task_id
        return self

    def set_question(self, question: str) -> "TaskStateBuilder":
        """Set question."""
        self._state["question"] = question
        return self

    def set_status(self, status: str) -> "TaskStateBuilder":
        """Set status."""
        self._state["status"] = status
        self._state["updated_at"] = datetime.now().isoformat()
        return self

    def add_observation(self, observation: dict[str, Any]) -> "TaskStateBuilder":
        """Add an observation."""
        self._state.setdefault("observations", []).append(observation)
        return self

    def add_claim(self, claim: dict[str, Any]) -> "TaskStateBuilder":
        """Add a claim."""
        self._state.setdefault("claims", []).append(claim)
        return self

    def update_hypothesis(self, hypothesis_id: str, updates: dict[str, Any]) -> "TaskStateBuilder":
        """Update a hypothesis."""
        hypotheses = self._state.setdefault("hypotheses", [])
        for i, h in enumerate(hypotheses):
            if h.get("hypothesis_id") == hypothesis_id:
                hypotheses[i].update(updates)
                break
        return self

    def set_current_step(self, step_id: str) -> "TaskStateBuilder":
        """Set current step."""
        self._state["current_step_id"] = step_id
        return self

    def save(self, create_checkpoint: bool = True) -> str:
        """Save state.

        Args:
            create_checkpoint: Whether to create checkpoint

        Returns:
            Checkpoint ID
        """
        task_id = self._state.get("task_id", "")
        if not task_id:
            raise ValueError("task_id required")

        return self._state_manager.save_state(
            task_id=task_id,
            state=self._state,
            create_checkpoint=create_checkpoint,
        )

    def build(self) -> dict[str, Any]:
        """Build state dict."""
        return self._state.copy()


def create_state_manager(
    storage_type: StateStorageType = StateStorageType.FILE,
    storage_path: str | None = None,
    max_checkpoints: int = 10,
) -> DurableStateManager:
    """Create a state manager.

    Args:
        storage_type: Storage type
        storage_path: Custom storage path
        max_checkpoints: Max checkpoints per task

    Returns:
        State manager
    """
    return DurableStateManager(
        storage_type=storage_type,
        storage_path=storage_path,
        max_checkpoints=max_checkpoints,
    )
