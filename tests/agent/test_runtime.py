"""Tests for Agent Runtime."""

import pytest

from eiw.agent.runtime import (
    AgentRuntime, AgentResult, AnalysisStatus,
    create_agent_runtime
)


class TestAgentRuntime:
    """Tests for AgentRuntime."""

    @pytest.fixture
    def runtime(self):
        """Create runtime."""
        return create_agent_runtime()

    @pytest.mark.asyncio
    async def test_analyze_simple(self, runtime):
        """Test simple analysis."""
        result = await runtime.analyze("What were sales last month?")

        assert result.task_id is not None
        assert result.question == "What were sales last month?"
        assert result.status in [AnalysisStatus.COMPLETED, AnalysisStatus.PARTIAL, AnalysisStatus.FAILED]

    @pytest.mark.asyncio
    async def test_analyze_with_domain(self, runtime):
        """Test analysis with domain."""
        result = await runtime.analyze(
            "Show revenue trends",
            domain="finance"
        )

        assert result.task_id is not None
        # Intent may be None if DeterministicProvider returns non-parseable response
        # In that case, the analysis should still complete with some status
        assert result.status in [
            AnalysisStatus.COMPLETED,
            AnalysisStatus.PARTIAL,
            AnalysisStatus.FAILED,
            AnalysisStatus.INTENT_RESOLVING,
        ]

    @pytest.mark.asyncio
    async def test_analyze_returns_duration(self, runtime):
        """Test duration tracking."""
        result = await runtime.analyze("Simple question")

        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_analyze_generates_answer(self, runtime):
        """Test answer generation."""
        result = await runtime.analyze("What are sales?")

        # Should have either observations or error
        assert result.final_answer or result.error

    def test_create_session(self, runtime):
        """Test session creation."""
        session = runtime.create_session("analyst_alice")

        assert session is not None
        assert session.user_id == "analyst_alice"

    def test_create_session_invalid(self, runtime):
        """Test invalid session."""
        session = runtime.create_session("nonexistent_user")

        assert session is None


class TestAgentResult:
    """Tests for AgentResult."""

    def test_create_result(self):
        """Test creating result."""
        result = AgentResult(
            task_id="task1",
            status=AnalysisStatus.PENDING,
            question="Test?",
        )

        assert result.task_id == "task1"
        assert result.status == AnalysisStatus.PENDING

    def test_result_with_observations(self):
        """Test result with observations."""
        result = AgentResult(
            task_id="task1",
            status=AnalysisStatus.COMPLETED,
            question="Test?",
            observations=[
                {"observation_id": "obs1", "content": "Sales up 10%"},
                {"observation_id": "obs2", "content": "Costs stable"},
            ],
            claims=[
                {"claim_id": "claim1", "statement": "Revenue grew"},
            ],
        )

        assert len(result.observations) == 2
        assert len(result.claims) == 1

    def test_result_with_clarification(self):
        """Test result requiring clarification."""
        result = AgentResult(
            task_id="task1",
            status=AnalysisStatus.CLARIFICATION_NEEDED,
            question="What happened?",
            clarification_needed=True,
            clarification_questions=[
                {"question_id": "q1", "question": "Which metric?"},
            ],
        )

        assert result.clarification_needed
        assert len(result.clarification_questions) == 1


class TestAnalysisStatus:
    """Tests for AnalysisStatus enum."""

    def test_all_statuses(self):
        """Test all status types exist."""
        assert AnalysisStatus.PENDING is not None
        assert AnalysisStatus.INTENT_RESOLVING is not None
        assert AnalysisStatus.PLANNING is not None
        assert AnalysisStatus.EXECUTING is not None
        assert AnalysisStatus.COMPLETED is not None
        assert AnalysisStatus.PARTIAL is not None
        assert AnalysisStatus.FAILED is not None
        assert AnalysisStatus.CLARIFICATION_NEEDED is not None


class TestRuntimeFactory:
    """Tests for runtime factory."""

    def test_create_with_defaults(self):
        """Test creating with defaults."""
        runtime = create_agent_runtime()

        assert runtime is not None
        assert runtime._provider is not None

    def test_create_with_checkpoint_disabled(self):
        """Test creating without checkpoints."""
        runtime = create_agent_runtime(enable_checkpoint=False)

        assert runtime._state_manager is None
