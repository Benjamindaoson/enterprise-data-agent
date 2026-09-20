"""Tests for Supervisor Runtime."""

import pytest

from eiw.agent.supervisor import (
    Supervisor, SupervisorDecision, AnalysisTask,
    TaskStatus, Hypothesis, HypothesisStatus,
    ConfidenceCategory, Observation, create_supervisor
)


class TestSupervisor:
    """Tests for Supervisor."""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor."""
        return create_supervisor(max_retries=2, max_budget_ms=10000)

    def test_create_supervisor(self, supervisor):
        """Test supervisor creation."""
        assert supervisor is not None
        assert supervisor._max_retries == 2
        assert supervisor._max_budget_ms == 10000

    def test_register_tool(self, supervisor):
        """Test tool registration."""
        async def mock_handler(**kwargs):
            return {"result": "success"}

        supervisor.register_tool(
            "test_tool",
            mock_handler
        )
        # Registration should not raise


class TestAnalysisTask:
    """Tests for AnalysisTask."""

    def test_create_task(self):
        """Test creating a task."""
        task = AnalysisTask(
            task_id="task1",
            question="What are sales?",
        )

        assert task.task_id == "task1"
        assert task.status == TaskStatus.CREATED
        assert task.observations == []

    def test_task_status_transitions(self):
        """Test task status changes."""
        task = AnalysisTask(
            task_id="task1",
            question="Test",
        )

        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED


class TestHypothesis:
    """Tests for Hypothesis."""

    def test_create_hypothesis(self):
        """Test creating a hypothesis."""
        hypothesis = Hypothesis(
            hypothesis_id="hyp1",
            statement="Sales increased due to marketing campaign",
            hypothesis_type="causal",
        )

        assert hypothesis.hypothesis_id == "hyp1"
        assert hypothesis.status == HypothesisStatus.PROPOSED
        assert hypothesis.confidence_category == ConfidenceCategory.NONE

    def test_hypothesis_support(self):
        """Test adding supporting evidence."""
        hypothesis = Hypothesis(
            hypothesis_id="hyp1",
            statement="Test",
            hypothesis_type="causal",
        )

        hypothesis.support("obs1")
        hypothesis.support("obs2")

        assert len(hypothesis.evidence_for) == 2
        assert hypothesis.confidence_category in [
            ConfidenceCategory.LOW, ConfidenceCategory.MEDIUM
        ]

    def test_hypothesis_weaken(self):
        """Test adding weakening evidence."""
        hypothesis = Hypothesis(
            hypothesis_id="hyp1",
            statement="Test",
            hypothesis_type="causal",
        )

        hypothesis.weaken("obs1")

        assert len(hypothesis.evidence_against) == 1
        assert hypothesis.status == HypothesisStatus.REFUTED

    def test_hypothesis_to_dict(self):
        """Test hypothesis serialization."""
        hypothesis = Hypothesis(
            hypothesis_id="hyp1",
            statement="Test",
            hypothesis_type="causal",
        )

        data = hypothesis.to_dict()

        assert data["hypothesis_id"] == "hyp1"
        assert data["statement"] == "Test"
        assert data["status"] == "proposed"


class TestObservation:
    """Tests for Observation."""

    def test_create_observation(self):
        """Test creating an observation."""
        observation = Observation(
            observation_id="obs1",
            tool_execution_id="exec1",
            content="Sales increased by 15%",
            data={"sales": 15000, "previous": 13000},
        )

        assert observation.observation_id == "obs1"
        assert "increased" in observation.content

    def test_observation_to_dict(self):
        """Test observation serialization."""
        observation = Observation(
            observation_id="obs1",
            tool_execution_id="exec1",
            content="Test",
            data={"value": 100},
        )

        data = observation.to_dict()

        assert data["observation_id"] == "obs1"
        assert "timestamp" in data


class TestSupervisorDecision:
    """Tests for SupervisorDecision enum."""

    def test_all_decisions(self):
        """Test all decision types exist."""
        assert SupervisorDecision.EXECUTE_STEP is not None
        assert SupervisorDecision.REFINED_PLAN is not None
        assert SupervisorDecision.DRILL_DOWN is not None
        assert SupervisorDecision.REQUEST_CLARIFICATION is not None
        assert SupervisorDecision.RETRY is not None
        assert SupervisorDecision.SYNTHESIZE is not None
        assert SupervisorDecision.COMPLETE_PARTIAL is not None
        assert SupervisorDecision.STOP_FAILED is not None
        assert SupervisorDecision.STOP_SUCCESS is not None
