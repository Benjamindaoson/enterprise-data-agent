"""Executor - Multi-Agent specialized execution interfaces.

This module provides:
- Executor protocol definition
- Executor category enum
- Step context for executor communication
- Base executor implementation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from eiw.agent.planner import ToolType


# =============================================================================
# Executor Categories
# =============================================================================


class ExecutorCategory(str, Enum):
    """Categories of specialized executors."""

    FINANCE = "finance"  # Financial analysis executor
    SALES = "sales"  # Sales analysis executor
    SUPPLY_CHAIN = "supply_chain"  # Supply chain analysis executor
    NL2SQL = "nl2sql"  # NL2SQL query executor
    ANALYTICS = "analytics"  # General analytics executor
    KNOWLEDGE = "knowledge"  # Knowledge retrieval executor
    PYTHON = "python"  # Python analysis executor
    CHART = "chart"  # Chart generation executor
    REPORT = "report"  # Report generation executor
    DEFAULT = "default"  # Default executor for unmatched tools


# =============================================================================
# Step Context
# =============================================================================


class StepContext(BaseModel):
    """Context passed to executors for step execution."""

    task_id: str = Field(description="Current task ID")
    plan_id: str = Field(description="Current plan ID")
    step_id: str = Field(description="Current step ID")

    # Intent and plan
    intent: dict[str, Any] = Field(default_factory=dict, description="Resolved intent")
    plan_summary: str = Field(default="", description="Plan summary")
    hypotheses: list[dict[str, Any]] = Field(default_factory=list, description="Current hypotheses")

    # Previous observations
    previous_observations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Previous observations for context"
    )

    # User context
    user_id: str = Field(default="", description="User ID")
    roles: list[str] = Field(default_factory=list, description="User roles")
    allowed_metrics: list[str] = Field(default_factory=list, description="Allowed metrics")
    allowed_dimensions: list[str] = Field(default_factory=list, description="Allowed dimensions")

    # Budget
    remaining_budget_ms: int = Field(default=60000, description="Remaining time budget")
    step_budget_ms: int = Field(default=5000, description="Budget for this step")

    # Metadata
    domain: str = Field(default="", description="Business domain")
    trace_id: str | None = Field(default=None, description="Trace ID for observability")
    created_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Executor Result
# =============================================================================


class ExecutorResult(BaseModel):
    """Result from executor execution."""

    success: bool = Field(description="Whether execution succeeded")
    step_id: str = Field(description="Step ID that was executed")

    # Output
    data: Any = Field(default=None, description="Execution result data")
    observation_id: str | None = Field(default=None, description="Created observation ID")
    claim_ids: list[str] = Field(default_factory=list, description="Created claim IDs")

    # Execution metadata
    duration_ms: float = Field(default=0.0, description="Execution duration in ms")
    tool_calls: int = Field(default=0, description="Number of tool calls made")
    tokens_used: int = Field(default=0, description="Tokens consumed")

    # Status
    status: str = Field(default="success", description="Execution status")
    error: str | None = Field(default=None, description="Error message if failed")
    warnings: list[str] = Field(default_factory=list, description="Execution warnings")

    # Provenance
    executed_at: datetime = Field(default_factory=datetime.now)
    executor_category: ExecutorCategory | None = Field(
        default=None,
        description="Executor that executed"
    )


# =============================================================================
# Executor Protocol
# =============================================================================


@runtime_checkable
class Executor(Protocol):
    """Protocol for specialized executors.

    Executors are responsible for executing specific categories of analysis steps.
    The Supervisor routes steps to appropriate executors based on tool type.
    """

    @property
    def category(self) -> ExecutorCategory:
        """Return the executor category."""
        ...

    @property
    def name(self) -> str:
        """Return the executor name."""
        ...

    @property
    def description(self) -> str:
        """Return the executor description."""
        ...

    def supported_tool_types(self) -> set[str]:
        """Return set of supported tool types."""
        ...

    def can_handle(self, tool_type: "ToolType | str") -> bool:
        """Check if this executor can handle the given tool type."""
        ...

    async def execute(
        self,
        context: StepContext,
        tool_type: "ToolType",
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute a step with the given tool.

        Args:
            context: Step execution context
            tool_type: Tool type to execute
            inputs: Tool-specific inputs

        Returns:
            Executor result
        """
        ...


# =============================================================================
# Base Executor
# =============================================================================


class BaseExecutor(ABC):
    """Base class for executors with common functionality."""

    def __init__(
        self,
        category: ExecutorCategory,
        name: str,
        description: str,
        supported_tools: set[str],
    ):
        self._category = category
        self._name = name
        self._description = description
        self._supported_tools = supported_tools

    @property
    def category(self) -> ExecutorCategory:
        return self._category

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def supported_tool_types(self) -> set[str]:
        return self._supported_tools.copy()

    def can_handle(self, tool_type: "ToolType | str") -> bool:
        """Check if this executor handles the given tool type."""
        tool_str = tool_type.value if hasattr(tool_type, "value") else str(tool_type)
        return tool_str in self._supported_tools


# =============================================================================
# Executor Registry
# =============================================================================


class ExecutorRegistry:
    """Registry for managing executor instances."""

    def __init__(self):
        self._executors: dict[ExecutorCategory, Executor] = {}
        self._tool_to_executor: dict[str, ExecutorCategory] = {}

    def register(self, executor: Executor) -> None:
        """Register an executor.

        Args:
            executor: Executor to register
        """
        self._executors[executor.category] = executor

        # Build tool-to-executor mapping
        for tool in executor.supported_tool_types():
            self._tool_to_executor[tool] = executor.category

    def get_executor(self, category: ExecutorCategory) -> Executor | None:
        """Get executor by category.

        Args:
            category: Executor category

        Returns:
            Executor instance or None
        """
        return self._executors.get(category)

    def get_executor_for_tool(self, tool_type: "ToolType | str") -> Executor | None:
        """Get executor for a tool type.

        Args:
            tool_type: Tool type to find executor for

        Returns:
            Executor that handles this tool type, or None
        """
        tool_str = tool_type.value if hasattr(tool_type, "value") else str(tool_type)
        category = self._tool_to_executor.get(tool_str)

        if category:
            return self._executors.get(category)

        # Fallback to default executor
        return self._executors.get(ExecutorCategory.DEFAULT)

    def list_executors(self) -> list[Executor]:
        """List all registered executors."""
        return list(self._executors.values())

    def get_executor_categories(self) -> list[ExecutorCategory]:
        """Get list of registered executor categories."""
        return list(self._executors.keys())


# =============================================================================
# Default Executor Registry
# =============================================================================


def create_default_executor_registry() -> ExecutorRegistry:
    """Create registry with default executors.

    Returns:
        Configured ExecutorRegistry
    """
    from eiw.agent.executors.analytics import AnalyticsExecutor
    from eiw.agent.executors.chart import ChartExecutor
    from eiw.agent.executors.default import DefaultExecutor
    from eiw.agent.executors.finance import FinanceExecutor
    from eiw.agent.executors.knowledge import KnowledgeExecutor
    from eiw.agent.executors.nl2sql import NL2SQLExecutor
    from eiw.agent.executors.python import PythonExecutor
    from eiw.agent.executors.report import ReportExecutor
    from eiw.agent.executors.sales import SalesExecutor
    from eiw.agent.executors.supply_chain import SupplyChainExecutor

    registry = ExecutorRegistry()

    # Register all default executors
    executors: list[Executor] = [
        FinanceExecutor(),
        SalesExecutor(),
        SupplyChainExecutor(),
        NL2SQLExecutor(),
        AnalyticsExecutor(),
        KnowledgeExecutor(),
        PythonExecutor(),
        ChartExecutor(),
        ReportExecutor(),
        DefaultExecutor(),
    ]

    for executor in executors:
        registry.register(executor)

    return registry
