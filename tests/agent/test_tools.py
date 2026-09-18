"""Tests for Tool Registry and Analytics Tools."""

import pytest

from eiw.agent.tools import (
    ToolRegistry, ToolCategory, ToolSignature, ToolExecutionContext,
    NL2SQLTool, TrendAnalysisTool, PeriodComparisonTool,
    ContributionAnalysisTool, PriceVolumeMixTool, VarianceAnalysisTool,
    DrilldownTool, AnomalyDetectionTool, PythonAnalysisTool,
    create_tool_registry
)


class TestToolRegistry:
    """Tests for ToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Create tool registry with tools."""
        return create_tool_registry()

    def test_register_tool(self, registry):
        """Test registering a tool."""
        async def mock_handler(params, ctx):
            return {"result": "success"}

        signature = ToolSignature(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.NL2SQL,
            parameters={"input": {"type": "string"}},
            returns={"type": "object"},
        )

        registry.register("test_tool", signature, mock_handler)

        assert registry.get("test_tool") is not None
        assert registry.get("test_tool").name == "test_tool"

    def test_get_by_category(self, registry):
        """Test getting tools by category."""
        async def mock_handler(params, ctx):
            return {}

        # Register multiple tools
        registry.register(
            "tool1",
            ToolSignature(
                name="tool1",
                description="Tool 1",
                category=ToolCategory.TREND,
                parameters={},
                returns={},
            ),
            mock_handler
        )
        registry.register(
            "tool2",
            ToolSignature(
                name="tool2",
                description="Tool 2",
                category=ToolCategory.TREND,
                parameters={},
                returns={},
            ),
            mock_handler
        )

        trend_tools = registry.get_by_category(ToolCategory.TREND)
        assert len(trend_tools) >= 2  # trend_analysis + mock tools

    @pytest.mark.asyncio
    async def test_execute_tool(self, registry):
        """Test executing a tool."""
        async def mock_handler(params, ctx):
            return {"output": params.get("input", "")}

        signature = ToolSignature(
            name="echo",
            description="Echo input",
            category=ToolCategory.NL2SQL,
            parameters={"input": {"type": "string"}},
            returns={"type": "object"},
        )

        registry.register("echo", signature, mock_handler)

        context = ToolExecutionContext(task_id="test")
        result = await registry.execute("echo", {"input": "hello"}, context)

        assert result.success
        assert result.data["output"] == "hello"

    def test_select_tools(self, registry):
        """Test tool selection."""
        intent = {"objective": "analyze trends"}
        tools = registry.select_tools(intent, "trend")
        assert "nl2sql_query" in tools or "trend_analysis" in tools


class TestTrendAnalysisTool:
    """Tests for TrendAnalysisTool."""

    @pytest.fixture
    def tool(self):
        """Create tool."""
        return TrendAnalysisTool()

    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test trend analysis execution."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "metric": "revenue",
            "time_granularity": "month",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
        }, context)

        assert "trend" in result
        assert "direction" in result
        assert "magnitude" in result


class TestPeriodComparisonTool:
    """Tests for PeriodComparisonTool."""

    @pytest.fixture
    def tool(self):
        """Create tool."""
        return PeriodComparisonTool()

    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test period comparison execution."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "metric": "revenue",
            "current_period_start": "2024-01-01",
            "current_period_end": "2024-03-31",
            "comparison_period_start": "2023-01-01",
            "comparison_period_end": "2023-03-31",
        }, context)

        assert "current_value" in result
        assert "comparison_value" in result
        assert "change" in result
        assert "change_percent" in result


class TestContributionAnalysisTool:
    """Tests for ContributionAnalysisTool."""

    @pytest.fixture
    def tool(self):
        """Create tool."""
        return ContributionAnalysisTool()

    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test contribution analysis execution."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "metric": "revenue",
            "dimension": "region",
            "period": "2024-Q1",
        }, context)

        assert "total" in result
        assert "contributions" in result
        assert len(result["contributions"]) > 0


class TestPriceVolumeMixTool:
    """Tests for PriceVolumeMixTool."""

    @pytest.fixture
    def tool(self):
        """Create tool."""
        return PriceVolumeMixTool()

    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test PVM analysis execution."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "metric": "revenue",
            "current_period": "2024-Q1",
            "comparison_period": "2023-Q1",
        }, context)

        assert "price_effect" in result
        assert "volume_effect" in result
        assert "mix_effect" in result


class TestVarianceAnalysisTool:
    """Tests for VarianceAnalysisTool."""

    @pytest.fixture
    def tool(self):
        """Create tool."""
        return VarianceAnalysisTool()

    @pytest.mark.asyncio
    async def test_execute_favorable(self, tool):
        """Test favorable variance."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "metric": "revenue",
            "actual_value": 120000,
            "budget_value": 100000,
        }, context)

        assert result["variance"] == 20000
        assert result["favorable"] is True

    @pytest.mark.asyncio
    async def test_execute_unfavorable(self, tool):
        """Test unfavorable variance."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "metric": "costs",
            "actual_value": 120000,
            "budget_value": 100000,
        }, context)

        assert result["variance"] == 20000
        assert result["favorable"] is False


class TestDrilldownTool:
    """Tests for DrilldownTool."""

    @pytest.fixture
    def tool(self):
        """Create tool."""
        return DrilldownTool()

    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test drilldown execution."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "metric": "sales",
            "from_dimension": "region",
            "to_dimension": "product",
            "filter_value": "North America",
            "period": "2024-Q1",
        }, context)

        assert "rows" in result
        assert len(result["rows"]) > 0


class TestAnomalyDetectionTool:
    """Tests for AnomalyDetectionTool."""

    @pytest.fixture
    def tool(self):
        """Create tool."""
        return AnomalyDetectionTool()

    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test anomaly detection execution."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "metric": "orders",
            "period": "2024",
            "sensitivity": 2.0,
        }, context)

        assert "anomalies" in result


class TestPythonAnalysisTool:
    """Tests for PythonAnalysisTool."""

    @pytest.fixture
    def tool(self):
        """Create tool."""
        return PythonAnalysisTool(sandbox_enabled=True)

    @pytest.mark.asyncio
    async def test_execute_simple(self, tool):
        """Test simple Python execution."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "code": "result = data.get('value', 0) * 2",
            "data": {"value": 21}
        }, context)

        assert result["error"] is None
        assert result["result"] == 42

    @pytest.mark.asyncio
    async def test_sandbox_blocks_os(self, tool):
        """Test that sandbox blocks os module."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "code": "import os; result = os.getcwd()",
            "data": {}
        }, context)

        assert result["error"] is not None
        assert "Blocked" in result["error"]

    @pytest.mark.asyncio
    async def test_sandbox_blocks_subprocess(self, tool):
        """Test that sandbox blocks subprocess."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "code": "import subprocess; result = subprocess.run(['ls'])",
            "data": {}
        }, context)

        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_allowed_math(self, tool):
        """Test that math module is allowed."""
        context = ToolExecutionContext()
        result = await tool.execute({
            "code": "import math; result = math.sqrt(16)",
            "data": {}
        }, context)

        assert result["error"] is None
        assert result["result"] == 4.0


class TestCreateToolRegistry:
    """Tests for tool registry factory."""

    def test_create_with_defaults(self):
        """Test creating registry with defaults."""
        registry = create_tool_registry()
        tools = registry.list_all()

        # Should have multiple tools registered
        assert len(tools) >= 8

    def test_nl2sql_registered(self):
        """Test NL2SQL tool is registered."""
        registry = create_tool_registry()
        tool = registry.get("nl2sql_query")

        assert tool is not None
        assert tool.category == ToolCategory.NL2SQL
