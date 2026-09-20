"""Agent Executors Package.

This package contains specialized executors for different analysis domains:
- FinanceExecutor: Financial analysis operations
- SalesExecutor: Sales analysis operations
- SupplyChainExecutor: Supply chain analysis operations
- NL2SQLExecutor: Natural language to SQL conversion
- AnalyticsExecutor: General analytics operations
- KnowledgeExecutor: Knowledge retrieval operations
- PythonExecutor: Python analysis sandbox
- ChartExecutor: Chart generation
- ReportExecutor: Report generation
- DefaultExecutor: Fallback executor for unmatched tools
"""

from eiw.agent.executor import (
    BaseExecutor,
    Executor,
    ExecutorCategory,
    ExecutorRegistry,
    ExecutorResult,
    StepContext,
    create_default_executor_registry,
)

__all__ = [
    "Executor",
    "ExecutorCategory",
    "ExecutorResult",
    "StepContext",
    "BaseExecutor",
    "ExecutorRegistry",
    "create_default_executor_registry",
]
