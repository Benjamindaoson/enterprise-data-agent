"""
测试模块
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pytest
from src.agent.executor import ActionExecutor
from src.agent.planner import PlanningEngine
from src.tools.registry import ToolRegistry


def test_executor_basic():
    """测试执行器基本功能"""
    def add(a, b):
        return a + b

    executor = ActionExecutor({"add": add})
    result = executor.execute("add", {"a": 1, "b": 2})
    assert result == "3"


def test_executor_error():
    """测试执行器错误处理"""
    def error_func():
        raise ValueError("测试错误")

    executor = ActionExecutor({"error": error_func})
    result = executor.execute("error", {})
    assert "执行错误" in result


def test_planner_should_act():
    """测试规划引擎"""
    planner = PlanningEngine([], {})

    class MockResponse:
        tool_calls = None

    assert planner.should_act(MockResponse()) == False


def test_tool_registry():
    """测试工具注册器"""
    registry = ToolRegistry()
    tools = registry.list_tools()

    assert "sql_inter" in tools
    assert "extract_data" in tools
    assert "python_inter" in tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
