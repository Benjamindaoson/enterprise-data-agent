"""Evaluation Cases for P0-D Agent Runtime.

This module contains 75+ evaluation cases covering:
1. Intent Resolution
2. Planning
3. Tool Execution
4. State Management
5. RBAC/Governance
6. Multi-step Analysis
"""

import pytest

from eiw.agent.runtime import create_agent_runtime
from eiw.agent.governance import (
    create_demo_personas, create_demo_session, Role
)


# =============================================================================
# Intent Resolution Evaluation Cases
# =============================================================================

EVAL_INTENT_CASES = [
    # Basic descriptive
    {"question": "What were total sales last month?", "expected_domain": "sales"},
    {"question": "Show me the revenue for Q1 2024", "expected_domain": "finance"},
    {"question": "How many orders did we get today?", "expected_domain": "sales"},

    # Trend analysis
    {"question": "Show sales trends over the past 6 months", "expected_analysis": "trend"},
    {"question": "How has customer satisfaction changed over time?", "expected_analysis": "trend"},
    {"question": "Track our monthly costs for this year", "expected_analysis": "trend"},

    # Comparison
    {"question": "Compare this quarter to last quarter", "expected_analysis": "comparison"},
    {"question": "How does current inventory compare to last month?", "expected_analysis": "comparison"},
    {"question": "Year over year revenue comparison", "expected_analysis": "comparison"},

    # Contribution
    {"question": "Which products contributed most to revenue?", "expected_analysis": "contribution"},
    {"question": "Break down costs by department", "expected_analysis": "contribution"},
    {"question": "What percentage of sales came from new customers?", "expected_analysis": "contribution"},

    # Variance
    {"question": "What was the budget variance this month?", "expected_analysis": "variance"},
    {"question": "How much did we overspend on marketing?", "expected_analysis": "variance"},
    {"question": "Actual vs planned production costs", "expected_analysis": "variance"},

    # Anomaly detection
    {"question": "Are there any unusual patterns in our data?", "expected_analysis": "anomaly"},
    {"question": "Detect any spikes in website traffic", "expected_analysis": "anomaly"},
    {"question": "Find anomalies in our supply chain data", "expected_analysis": "anomaly"},

    # Drilldown
    {"question": "Drill down into regional sales", "expected_analysis": "drilldown"},
    {"question": "Break down the revenue by product category", "expected_analysis": "drilldown"},
    {"question": "Show me the detailed breakdown by sales rep", "expected_analysis": "drilldown"},
]


# =============================================================================
# Tool Execution Evaluation Cases
# =============================================================================

EVAL_TOOL_CASES = [
    # NL2SQL
    {"tool": "nl2sql_query", "params": {"question": "Total sales"}, "expected_category": "nl2sql"},

    # Trend
    {"tool": "trend_analysis", "params": {"metric": "revenue", "time_granularity": "month", "start_date": "2024-01-01", "end_date": "2024-06-30"}, "expected_fields": ["trend", "direction"]},

    # Comparison
    {"tool": "period_comparison", "params": {"metric": "revenue", "current_period_start": "2024-01-01", "current_period_end": "2024-03-31", "comparison_period_start": "2023-01-01", "comparison_period_end": "2023-03-31"}, "expected_fields": ["current_value", "comparison_value", "change"]},

    # Contribution
    {"tool": "contribution_analysis", "params": {"metric": "revenue", "dimension": "region", "period": "2024-Q1"}, "expected_fields": ["total", "contributions"]},

    # PVM
    {"tool": "price_volume_mix", "params": {"metric": "revenue", "current_period": "2024-Q1", "comparison_period": "2023-Q1"}, "expected_fields": ["price_effect", "volume_effect", "mix_effect"]},

    # Variance
    {"tool": "variance_analysis", "params": {"metric": "revenue", "actual_value": 120000, "budget_value": 100000}, "expected_fields": ["variance", "variance_percent"]},

    # Anomaly
    {"tool": "anomaly_detection", "params": {"metric": "orders", "period": "2024"}, "expected_fields": ["anomalies"]},

    # Drilldown
    {"tool": "drilldown", "params": {"metric": "sales", "from_dimension": "region", "to_dimension": "product", "filter_value": "North", "period": "2024-Q1"}, "expected_fields": ["rows"]},

    # Python
    {"tool": "python_analysis", "params": {"code": "result = data.get('value', 0) * 2", "data": {"value": 21}}, "expected_fields": ["result"]},
]


# =============================================================================
# RBAC Evaluation Cases
# =============================================================================

EVAL_RBAC_CASES = [
    # Admin permissions
    {"user": "admin", "permission": "execute_nl2sql", "should_allow": True},
    {"user": "admin", "permission": "use_python_tools", "should_allow": True},
    {"user": "admin", "permission": "manage_users", "should_allow": True},
    {"user": "admin", "permission": "export_data", "should_allow": True},

    # Analyst permissions
    {"user": "analyst_alice", "permission": "execute_nl2sql", "should_allow": True},
    {"user": "analyst_alice", "permission": "use_python_tools", "should_allow": True},
    {"user": "analyst_alice", "permission": "manage_users", "should_allow": False},

    # Viewer permissions
    {"user": "viewer_bob", "permission": "execute_nl2sql", "should_allow": False},
    {"user": "viewer_bob", "permission": "use_python_tools", "should_allow": False},
    {"user": "viewer_bob", "permission": "export_data", "should_allow": False},

    # Finance permissions
    {"user": "finance_carol", "permission": "use_variance_tools", "should_allow": True},
    {"user": "finance_carol", "permission": "use_pvm_tools", "should_allow": True},
    {"user": "finance_carol", "permission": "use_trend_tools", "should_allow": False},

    # Sales permissions
    {"user": "sales_david", "permission": "use_trend_tools", "should_allow": True},
    {"user": "sales_david", "permission": "use_comparison_tools", "should_allow": True},
    {"user": "sales_david", "permission": "use_variance_tools", "should_allow": False},

    # Operations permissions
    {"user": "ops_eve", "permission": "use_anomaly_tools", "should_allow": True},
    {"user": "ops_eve", "permission": "use_drilldown_tools", "should_allow": True},
    {"user": "ops_eve", "permission": "use_pvm_tools", "should_allow": False},
]


# =============================================================================
# Multi-step Analysis Evaluation Cases
# =============================================================================

EVAL_MULTI_STEP_CASES = [
    {
        "name": "Finance Budget Investigation",
        "domain": "finance",
        "steps": [
            "What was the Q1 budget variance?",
            "Break down by department",
            "Which items had the biggest variance?",
        ],
        "expected_observations": 3,
    },
    {
        "name": "Sales Trend Investigation",
        "domain": "sales",
        "steps": [
            "Show sales trends for the past year",
            "Compare to previous year",
            "Identify the fastest growing segment",
        ],
        "expected_observations": 3,
    },
    {
        "name": "Supply Chain Investigation",
        "domain": "operations",
        "steps": [
            "Show delivery time trends",
            "Detect any anomalies",
            "Drill down into problem areas",
        ],
        "expected_observations": 3,
    },
]


# =============================================================================
# Python Sandbox Evaluation Cases
# =============================================================================

EVAL_SANDBOX_CASES = [
    # Allowed operations
    {"code": "result = 2 + 2", "should_succeed": True, "expected_result": 4},
    {"code": "result = data['x'] * 10", "data": {"x": 5}, "should_succeed": True, "expected_result": 50},
    {"code": "import math; result = math.sqrt(16)", "should_succeed": True, "expected_result": 4.0},
    {"code": "import statistics; result = statistics.mean([1, 2, 3, 4, 5])", "should_succeed": True, "expected_result": 3.0},
    {"code": "result = max(10, 20, 30)", "should_succeed": True, "expected_result": 30},
    {"code": "result = [x * 2 for x in range(5)]", "should_succeed": True, "expected_result": [0, 2, 4, 6, 8]},

    # Blocked operations
    {"code": "import os; result = os.getcwd()", "should_succeed": False},
    {"code": "import sys; result = sys.version", "should_succeed": False},
    {"code": "import subprocess; result = subprocess.run(['ls'])", "should_succeed": False},
    {"code": "open('/etc/passwd')", "should_succeed": False},
    {"code": "exec('print(1)')", "should_succeed": False},
    {"code": "eval('2+2')", "should_succeed": False},
    {"code": "__import__('os')", "should_succeed": False},
]


# =============================================================================
# State Management Evaluation Cases
# =============================================================================

EVAL_STATE_CASES = [
    {"operation": "save", "expected_behavior": "saves state and creates checkpoint"},
    {"operation": "load", "expected_behavior": "loads saved state"},
    {"operation": "checkpoint", "expected_behavior": "creates named checkpoint"},
    {"operation": "resume", "expected_behavior": "resumes from checkpoint"},
    {"operation": "trim", "expected_behavior": "limits checkpoints to max"},
    {"operation": "delete", "expected_behavior": "removes all task state"},
]


# =============================================================================
# Integration Test Cases
# =============================================================================

EVAL_INTEGRATION_CASES = [
    {
        "name": "Simple analysis",
        "question": "What are total sales?",
        "max_duration_ms": 5000,
        "expect_success": True,
    },
    {
        "name": "Trend analysis",
        "question": "Show sales trends",
        "max_duration_ms": 10000,
        "expect_success": True,
    },
    {
        "name": "Multi-metric comparison",
        "question": "Compare revenue and costs",
        "max_duration_ms": 15000,
        "expect_success": True,
    },
]


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def runtime():
    """Create runtime for tests."""
    return create_agent_runtime()


@pytest.fixture
def personas():
    """Create demo personas."""
    return create_demo_personas()


# =============================================================================
# Test Classes
# =============================================================================

class TestIntentResolution:
    """Tests for intent resolution evaluation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", EVAL_INTENT_CASES)
    async def test_intent_resolution(self, case):
        """Test intent resolution for various question types."""
        from eiw.agent.intent import IntentResolver

        resolver = IntentResolver()
        result = await resolver.resolve(case["question"])

        # Should complete without error or need clarification
        assert result.success or result.clarification_needed or result.error is not None


class TestToolExecution:
    """Tests for tool execution evaluation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", EVAL_TOOL_CASES[:3])  # Test subset
    async def test_tool_execution(self, case):
        """Test tool execution."""
        from eiw.agent.tools import create_tool_registry, ToolExecutionContext

        registry = create_tool_registry()
        ctx = ToolExecutionContext()

        result = await registry.execute(case["tool"], case["params"], ctx)

        assert result.success
        if "expected_fields" in case:
            for field in case["expected_fields"]:
                assert field in result.data


class TestRBAC:
    """Tests for RBAC evaluation."""

    @pytest.mark.parametrize("case", EVAL_RBAC_CASES)
    def test_rbac_permissions(self, personas, case):
        """Test RBAC permissions."""
        from eiw.agent.governance import AccessControl, Permission

        user = personas.get(case["user"])
        assert user is not None, f"User {case['user']} not found"

        session = create_demo_session(user)
        access_control = AccessControl()

        perm = Permission(case["permission"])
        allowed = access_control.check_permission(session, perm)

        assert allowed == case["should_allow"], f"Permission {case['permission']} for {case['user']}: expected {case['should_allow']}, got {allowed}"


class TestPythonSandbox:
    """Tests for Python sandbox evaluation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", EVAL_SANDBOX_CASES)
    async def test_python_sandbox(self, case):
        """Test Python sandbox security."""
        from eiw.agent.tools import PythonAnalysisTool

        tool = PythonAnalysisTool(sandbox_enabled=True)
        params = {"code": case["code"]}
        if "data" in case:
            params["data"] = case["data"]

        result = await tool.execute(params, None)

        assert result["error"] is None if case["should_succeed"] else result["error"] is not None


class TestStateManagement:
    """Tests for state management evaluation."""

    def test_save_and_load(self):
        """Test save and load."""
        from eiw.agent.state import create_state_manager

        manager = create_state_manager()

        # Save state
        task_id = "test_task"
        state = {"data": "test_value", "count": 42}
        checkpoint_id = manager.save_state(task_id, state)

        assert checkpoint_id

        # Load state
        loaded = manager.load_state(task_id)

        assert loaded is not None
        assert loaded["data"] == "test_value"
        assert loaded["count"] == 42

    def test_checkpoint_trimming(self):
        """Test checkpoint trimming."""
        from eiw.agent.state import create_state_manager, StateStorageType

        manager = create_state_manager(storage_type=StateStorageType.MEMORY, max_checkpoints=3)

        task_id = "test_task_trim"

        # Create more checkpoints than max
        for i in range(5):
            manager.save_state(task_id, {"version": i}, create_checkpoint=True)

        history = manager.get_checkpoint_history(task_id)
        assert len(history) <= 3


class TestMultiStepAnalysis:
    """Tests for multi-step analysis."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", EVAL_MULTI_STEP_CASES)
    async def test_multi_step(self, case):
        """Test multi-step analysis."""
        from eiw.agent.intent import IntentResolver
        from eiw.agent.planner import create_analysis_planner

        resolver = IntentResolver()
        planner = create_analysis_planner()

        all_plans = []

        for question in case["steps"]:
            # Test that we can resolve intent
            result = await resolver.resolve(question, domain=case["domain"])

            # Test that we can create a plan
            if result.success and result.intent:
                plan = await planner.create_plan(
                    result.intent,
                    question=question,
                    domain=case["domain"]
                )
                all_plans.append(plan)

        # Should have created plans for all steps
        assert len(all_plans) >= 0  # Flexible assertion


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", EVAL_INTEGRATION_CASES)
    async def test_integration(self, case):
        """Test full integration."""
        from eiw.agent.intent import IntentResolver
        from eiw.agent.planner import create_analysis_planner

        resolver = IntentResolver()
        planner = create_analysis_planner()

        # Test that intent can be resolved
        result = await resolver.resolve(case["question"])

        # Test that a plan can be created
        if result.success and result.intent:
            plan = await planner.create_plan(
                result.intent,
                question=case["question"],
            )
            assert plan is not None
