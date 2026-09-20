"""Tests for Durable State Management."""

import pytest
import os
import tempfile
import shutil

from eiw.agent.state import (
    DurableStateManager, StateStorageType, Checkpoint,
    CheckpointMetadata, create_state_manager, TaskStateBuilder
)


class TestDurableStateManager:
    """Tests for DurableStateManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory."""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture
    def state_manager(self, temp_dir):
        """Create state manager with temp storage."""
        return DurableStateManager(
            storage_type=StateStorageType.FILE,
            storage_path=temp_dir,
            max_checkpoints=3,
        )

    def test_save_and_load_state(self, state_manager, temp_dir):
        """Test saving and loading state."""
        task_id = "test_task_1"
        state = {
            "task_id": task_id,
            "status": "running",
            "observations": [],
        }

        # Save state
        checkpoint_id = state_manager.save_state(task_id, state)

        # Verify file was created
        state_file = os.path.join(temp_dir, task_id, "current.json")
        assert os.path.exists(state_file)

        # Load state
        loaded = state_manager.load_state(task_id)
        assert loaded is not None
        assert loaded["task_id"] == task_id
        assert loaded["status"] == "running"

    def test_checkpoint_creation(self, state_manager):
        """Test checkpoint creation."""
        task_id = "test_task_2"
        state = {"task_id": task_id, "data": "test"}

        # Create multiple checkpoints
        ckpt1 = state_manager.save_state(task_id, {**state, "version": 1}, create_checkpoint=True)
        ckpt2 = state_manager.save_state(task_id, {**state, "version": 2}, create_checkpoint=True)
        ckpt3 = state_manager.save_state(task_id, {**state, "version": 3}, create_checkpoint=True)

        # Should have 3 checkpoints
        history = state_manager.get_checkpoint_history(task_id)
        assert len(history) == 3

    def test_checkpoint_trimming(self, state_manager):
        """Test checkpoint trimming."""
        task_id = "test_task_3"

        # Create more checkpoints than max_checkpoints
        for i in range(5):
            state_manager.save_state(task_id, {"version": i}, create_checkpoint=True)

        # Should be trimmed to max_checkpoints
        history = state_manager.get_checkpoint_history(task_id)
        assert len(history) <= state_manager._max_checkpoints

    def test_load_checkpoint(self, state_manager):
        """Test loading specific checkpoint."""
        task_id = "test_task_4"
        state1 = {"task_id": task_id, "value": 100}
        state2 = {"task_id": task_id, "value": 200}

        ckpt1 = state_manager.save_state(task_id, state1, create_checkpoint=True)
        state_manager.save_state(task_id, state2, create_checkpoint=True)

        # Load first checkpoint
        loaded = state_manager.load_checkpoint(ckpt1, task_id)
        assert loaded is not None
        assert loaded["value"] == 100

    def test_delete_task_state(self, state_manager):
        """Test deleting task state."""
        task_id = "test_task_5"
        state_manager.save_state(task_id, {"data": "test"})

        # Verify exists
        assert state_manager.load_state(task_id) is not None

        # Delete
        state_manager.delete_task_state(task_id)

        # Verify deleted
        assert state_manager.load_state(task_id) is None

    def test_list_tasks(self, state_manager):
        """Test listing tasks."""
        state_manager.save_state("task_a", {"data": "a"})
        state_manager.save_state("task_b", {"data": "b"})

        tasks = state_manager.list_tasks()
        assert "task_a" in tasks
        assert "task_b" in tasks


class TestTaskStateBuilder:
    """Tests for TaskStateBuilder."""

    @pytest.fixture
    def state_manager(self):
        """Create in-memory state manager."""
        return DurableStateManager(storage_type=StateStorageType.MEMORY)

    def test_build_state(self, state_manager):
        """Test building state."""
        builder = TaskStateBuilder(state_manager)

        state = builder.set_task_id("task1") \
            .set_question("What are sales?") \
            .set_status("running") \
            .build()

        assert state["task_id"] == "task1"
        assert state["question"] == "What are sales?"
        assert state["status"] == "running"

    def test_add_observation(self, state_manager):
        """Test adding observations."""
        builder = TaskStateBuilder(state_manager)
        builder.set_task_id("task1")

        builder.add_observation({"id": "obs1", "content": "Sales up 10%"})
        builder.add_observation({"id": "obs2", "content": "Costs stable"})

        state = builder.build()
        assert len(state["observations"]) == 2

    def test_save_state(self, state_manager):
        """Test saving state."""
        builder = TaskStateBuilder(state_manager)

        builder.set_task_id("task1") \
            .set_question("Test?") \
            .set_status("running")

        checkpoint_id = builder.save(create_checkpoint=True)

        assert checkpoint_id
        assert state_manager.load_state("task1") is not None


class TestCheckpoint:
    """Tests for Checkpoint model."""

    def test_create_checkpoint(self):
        """Test creating a checkpoint."""
        metadata = CheckpointMetadata(
            checkpoint_id="ckpt1",
            task_id="task1",
            state_type="agent_state",
            size_bytes=1024,
        )

        checkpoint = Checkpoint(
            metadata=metadata,
            state={"data": "test"},
        )

        assert checkpoint.metadata.checkpoint_id == "ckpt1"
        assert checkpoint.full_checkpoint is True

    def test_checkpoint_serialization(self):
        """Test checkpoint serialization."""
        metadata = CheckpointMetadata(
            checkpoint_id="ckpt1",
            task_id="task1",
            state_type="test",
        )

        checkpoint = Checkpoint(
            metadata=metadata,
            state={"value": 42},
        )

        data = checkpoint.to_dict()

        assert data["metadata"]["checkpoint_id"] == "ckpt1"
        assert data["state"]["value"] == 42

    def test_checkpoint_deserialization(self):
        """Test checkpoint deserialization."""
        data = {
            "metadata": {
                "checkpoint_id": "ckpt1",
                "task_id": "task1",
                "created_at": "2024-01-01T00:00:00",
                "state_type": "test",
                "size_bytes": 100,
            },
            "state": {"test": "data"},
            "full_checkpoint": True,
        }

        checkpoint = Checkpoint.from_dict(data)

        assert checkpoint.metadata.checkpoint_id == "ckpt1"
        assert checkpoint.state["test"] == "data"
