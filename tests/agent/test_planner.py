"""Tests for Analysis Planner."""

import pytest

from eiw.agent.planner import (
    AnalysisPlanner, AnalysisPlan, AnalysisStep,
    StepStatus, ToolType, create_analysis_planner
)


class TestAnalysisPlanner:
    """Tests for AnalysisPlanner."""

    @pytest.fixture
    def planner(self):
        """Create planner."""
        return create_analysis_planner()

    @pytest.mark.asyncio
    async def test_create_simple_plan(self, planner):
        """Test creating a simple plan."""
        from eiw.agent.intent import ResolvedBusinessIntent, AnalysisType

        intent = ResolvedBusinessIntent(
            objective="Analyze sales",
            domain="sales",
            analysis_type=AnalysisType.DESCRIPTIVE,
        )

        plan = await planner.create_plan(
            intent=intent,
            question="What were sales last month?",
            domain="sales",
        )

        assert plan is not None
        assert len(plan.steps) > 0
        assert plan.total_budget_ms > 0

    @pytest.mark.asyncio
    async def test_plan_completion(self, planner):
        """Test plan completion detection."""
        from eiw.agent.intent import ResolvedBusinessIntent, AnalysisType

        intent = ResolvedBusinessIntent(
            objective="Analyze",
            domain="sales",
            analysis_type=AnalysisType.DESCRIPTIVE,
        )

        plan = await planner.create_plan(
            intent=intent,
            question="Test",
            domain="sales",
        )

        # Initially not complete
        assert not plan.is_complete()

        # Complete all steps
        for step in plan.steps:
            plan.mark_step_complete(step.step_id)

        assert plan.is_complete()


class TestAnalysisStep:
    """Tests for AnalysisStep."""

    def test_create_step(self):
        """Test creating a step."""
        step = AnalysisStep(
            step_id="step1",
            purpose="Retrieve sales data",
            tool=ToolType.NL2SQL_QUERY,
            required_inputs={"question": "sales last month"},
        )

        assert step.step_id == "step1"
        assert step.tool == ToolType.NL2SQL_QUERY
        assert step.status == StepStatus.PENDING

    def test_step_dependencies(self):
        """Test step dependencies."""
        step1 = AnalysisStep(
            step_id="step1",
            purpose="Step 1",
            tool=ToolType.NL2SQL_QUERY,
        )
        step2 = AnalysisStep(
            step_id="step2",
            purpose="Step 2",
            tool=ToolType.TREND_ANALYSIS,
            dependencies=["step1"],
        )

        assert "step1" in step2.dependencies


class TestAnalysisPlan:
    """Tests for AnalysisPlan."""

    def test_create_plan(self):
        """Test creating a plan."""
        plan = AnalysisPlan(
            plan_id="plan1",
            intent_summary="Analyze sales",
            total_budget_ms=50000,
        )

        assert plan.plan_id == "plan1"
        assert plan.total_budget_ms == 50000
        assert len(plan.steps) == 0

    def test_add_step(self):
        """Test adding steps."""
        plan = AnalysisPlan(
            plan_id="plan1",
            intent_summary="Test",
        )

        step = AnalysisStep(
            step_id="step1",
            purpose="Test",
            tool=ToolType.NL2SQL_QUERY,
        )
        plan.steps.append(step)

        assert len(plan.steps) == 1

    def test_get_next_step(self):
        """Test getting next step."""
        plan = AnalysisPlan(
            plan_id="plan1",
            intent_summary="Test",
        )

        step1 = AnalysisStep(
            step_id="step1",
            purpose="Step 1",
            tool=ToolType.NL2SQL_QUERY,
        )
        step2 = AnalysisStep(
            step_id="step2",
            purpose="Step 2",
            tool=ToolType.TREND_ANALYSIS,
            dependencies=["step1"],
        )

        plan.steps.append(step1)
        plan.steps.append(step2)

        # First should be step1 (no dependencies)
        next_step = plan.get_next_step()
        assert next_step.step_id == "step1"

        # Complete step1
        plan.mark_step_complete("step1")

        # Now step2 should be available
        next_step = plan.get_next_step()
        assert next_step.step_id == "step2"

    def test_estimated_cost(self):
        """Test cost estimation."""
        plan = AnalysisPlan(
            plan_id="plan1",
            intent_summary="Test",
            total_budget_ms=50000,
        )

        step1 = AnalysisStep(
            step_id="step1",
            purpose="Step 1",
            tool=ToolType.NL2SQL_QUERY,
            budget_estimate_ms=10000,
        )
        plan.steps.append(step1)

        # Verify budget is sufficient
        total_estimated = sum(s.budget_estimate_ms for s in plan.steps)
        assert total_estimated <= plan.total_budget_ms


class TestToolType:
    """Tests for ToolType enum."""

    def test_tool_types(self):
        """Test all tool types exist."""
        assert ToolType.NL2SQL_QUERY is not None
        assert ToolType.TREND_ANALYSIS is not None
        assert ToolType.PERIOD_COMPARE is not None
        assert ToolType.CONTRIBUTION_ANALYSIS is not None
        assert ToolType.PVM_ANALYSIS is not None
        assert ToolType.VARIANCE_ANALYSIS is not None
        assert ToolType.DRILLDOWN_ANALYSIS is not None
        assert ToolType.ANOMALY_ANALYSIS is not None
        assert ToolType.PYTHON_ANALYSIS is not None

    def test_tool_type_cost_weights(self):
        """Test tool type cost weights."""
        # Check that all tools have reasonable weights
        for tool_type in ToolType:
            assert tool_type.value is not None
