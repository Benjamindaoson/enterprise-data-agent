"""Tests for Multi-Agent Executor System.

This module tests the Supervisor-Executor multi-agent architecture.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from eiw.agent import (
    ExecutorCategory,
    ExecutorRegistry,
    ExecutorResult,
    StepContext,
    create_default_executor_registry,
    create_supervisor,
)


class TestExecutorRegistry:
    """Tests for ExecutorRegistry."""

    def test_create_default_registry(self):
        """Test creating default executor registry."""
        registry = create_default_executor_registry()
        assert registry is not None
        assert len(registry.get_executor_categories()) >= 9

    def test_get_executor_by_category(self):
        """Test getting executor by category."""
        registry = create_default_executor_registry()

        finance_executor = registry.get_executor(ExecutorCategory.FINANCE)
        assert finance_executor is not None
        assert finance_executor.name == "finance"

        sales_executor = registry.get_executor(ExecutorCategory.SALES)
        assert sales_executor is not None
        assert sales_executor.name == "sales"

    def test_get_executor_for_tool(self):
        """Test getting executor for a specific tool type."""
        registry = create_default_executor_registry()

        # Test tool type routing
        tool_mappings = {
            "metric_query": ExecutorCategory.ANALYTICS,
            "trend_analysis": ExecutorCategory.SUPPLY_CHAIN,
            "knowledge_search": ExecutorCategory.KNOWLEDGE,
            "python_analysis": ExecutorCategory.PYTHON,
            "chart_generate": ExecutorCategory.CHART,
            "report_generate": ExecutorCategory.REPORT,
            "variance_analysis": ExecutorCategory.FINANCE,
            "period_compare": ExecutorCategory.SALES,
            "nl2sql_generate": ExecutorCategory.NL2SQL,
        }

        for tool_type, expected_category in tool_mappings.items():
            executor = registry.get_executor_for_tool(tool_type)
            assert executor is not None, f"No executor for tool: {tool_type}"
            assert executor.category == expected_category, f"Wrong executor for {tool_type}"


class TestStepContext:
    """Tests for StepContext."""

    def test_create_step_context(self):
        """Test creating a step context."""
        context = StepContext(
            task_id="test-task-001",
            plan_id="plan-001",
            step_id="step-001",
            intent={"query": "revenue analysis"},
            domain="finance",
        )

        assert context.task_id == "test-task-001"
        assert context.plan_id == "plan-001"
        assert context.step_id == "step-001"
        assert context.intent["query"] == "revenue analysis"
        assert context.domain == "finance"

    def test_default_values(self):
        """Test default values for step context."""
        context = StepContext(
            task_id="test-task",
            plan_id="plan-001",
            step_id="step-001",
        )

        assert context.remaining_budget_ms == 60000
        assert context.step_budget_ms == 5000
        assert context.hypotheses == []
        assert context.previous_observations == []


class TestExecutorExecution:
    """Tests for executor execution."""

    @pytest.fixture
    def registry(self):
        """Create executor registry."""
        return create_default_executor_registry()

    @pytest.fixture
    def context(self):
        """Create test context."""
        return StepContext(
            task_id="test-task-001",
            plan_id="plan-001",
            step_id="step-001",
        )

    @pytest.mark.asyncio
    async def test_finance_executor_metric_query(self, registry, context):
        """Test FinanceExecutor with metric_query."""
        executor = registry.get_executor_for_tool("metric_query")
        result = await executor.execute(
            context=context,
            tool_type="metric_query",
            inputs={"metrics": ["revenue"], "dimensions": ["region"]},
        )

        assert result.success is True
        assert result.executor_category == ExecutorCategory.ANALYTICS
        assert result.data is not None
        assert "metrics" in result.data

    @pytest.mark.asyncio
    async def test_sales_executor_period_compare(self, registry, context):
        """Test SalesExecutor with period_compare."""
        executor = registry.get_executor_for_tool("period_compare")
        result = await executor.execute(
            context=context,
            tool_type="period_compare",
            inputs={"period_type": "MoM", "metric": "revenue"},
        )

        assert result.success is True
        assert result.executor_category == ExecutorCategory.SALES
        assert result.data["period_type"] == "MoM"

    @pytest.mark.asyncio
    async def test_supply_chain_executor_trend(self, registry, context):
        """Test SupplyChainExecutor with trend_analysis."""
        executor = registry.get_executor_for_tool("trend_analysis")
        result = await executor.execute(
            context=context,
            tool_type="trend_analysis",
            inputs={"granularity": "weekly", "metric": "inventory"},
        )

        assert result.success is True
        assert result.executor_category == ExecutorCategory.SUPPLY_CHAIN
        assert result.data["granularity"] == "weekly"

    @pytest.mark.asyncio
    async def test_knowledge_executor_search(self, registry, context):
        """Test KnowledgeExecutor with knowledge_search."""
        executor = registry.get_executor_for_tool("knowledge_search")
        result = await executor.execute(
            context=context,
            tool_type="knowledge_search",
            inputs={"query": "best practices"},
        )

        assert result.success is True
        assert result.executor_category == ExecutorCategory.KNOWLEDGE

    @pytest.mark.asyncio
    async def test_python_executor_analysis(self, registry, context):
        """Test PythonExecutor with python_analysis."""
        executor = registry.get_executor_for_tool("python_analysis")
        result = await executor.execute(
            context=context,
            tool_type="python_analysis",
            inputs={"data": [1, 2, 3], "analysis_type": "descriptive"},
        )

        assert result.success is True
        assert result.executor_category == ExecutorCategory.PYTHON

    @pytest.mark.asyncio
    async def test_chart_executor_generate(self, registry, context):
        """Test ChartExecutor with chart_generate."""
        executor = registry.get_executor_for_tool("chart_generate")
        result = await executor.execute(
            context=context,
            tool_type="chart_generate",
            inputs={"chart_type": "line", "title": "Revenue Trend"},
        )

        assert result.success is True
        assert result.executor_category == ExecutorCategory.CHART
        assert result.data["chart_type"] == "line"

    @pytest.mark.asyncio
    async def test_report_executor_generate(self, registry, context):
        """Test ReportExecutor with report_generate."""
        executor = registry.get_executor_for_tool("report_generate")
        result = await executor.execute(
            context=context,
            tool_type="report_generate",
            inputs={"title": "Monthly Report", "sections": ["summary", "details"]},
        )

        assert result.success is True
        assert result.executor_category == ExecutorCategory.REPORT
        assert result.data["title"] == "Monthly Report"


class TestSupervisorIntegration:
    """Tests for Supervisor with Executor integration."""

    def test_supervisor_with_executor_registry(self):
        """Test supervisor accepts executor registry."""
        registry = create_default_executor_registry()
        supervisor = create_supervisor(executor_registry=registry)

        assert supervisor._executor_registry is registry

    def test_supervisor_select_executor(self):
        """Test supervisor can select appropriate executor."""
        registry = create_default_executor_registry()
        supervisor = create_supervisor(executor_registry=registry)

        from eiw.agent.planner import ToolType

        # Test various tool types
        test_cases = [
            (ToolType.METRIC_QUERY, ExecutorCategory.ANALYTICS),
            (ToolType.TREND_ANALYSIS, ExecutorCategory.SUPPLY_CHAIN),
            (ToolType.KNOWLEDGE_SEARCH, ExecutorCategory.KNOWLEDGE),
            (ToolType.PYTHON_ANALYSIS, ExecutorCategory.PYTHON),
        ]

        for tool_type, expected_category in test_cases:
            executor = supervisor._select_executor(tool_type)
            assert executor is not None, f"No executor for {tool_type}"
            assert executor.category == expected_category


class TestExecutorResult:
    """Tests for ExecutorResult."""

    def test_create_result(self):
        """Test creating an executor result."""
        result = ExecutorResult(
            success=True,
            step_id="step-001",
            data={"key": "value"},
            observation_id="obs-001",
            executor_category=ExecutorCategory.FINANCE,
        )

        assert result.success is True
        assert result.step_id == "step-001"
        assert result.data["key"] == "value"
        assert result.observation_id == "obs-001"
        assert result.executor_category == ExecutorCategory.FINANCE

    def test_result_with_error(self):
        """Test creating an error result."""
        result = ExecutorResult(
            success=False,
            step_id="step-001",
            error="Something went wrong",
            executor_category=ExecutorCategory.SALES,
        )

        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_optional_category(self):
        """Test result without executor category."""
        result = ExecutorResult(
            success=True,
            step_id="step-001",
        )

        assert result.success is True
        assert result.executor_category is None
