"""Tool Registry and Analytics Tool Suite.

This module provides:
- Typed tool definitions
- Tool registry
- Analytics tool implementations
- Tool execution
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, Field, ConfigDict

from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "tools")


# =============================================================================
# Tool Types
# =============================================================================


class ToolCategory(str, Enum):
    """Categories of tools."""

    NL2SQL = "nl2sql"  # Natural language to SQL
    TREND = "trend"  # Trend analysis
    COMPARISON = "comparison"  # Period comparison
    CONTRIBUTION = "contribution"  # Contribution analysis
    PVM = "pvm"  # Price volume mix
    VARIANCE = "variance"  # Variance analysis
    DRILLDOWN = "drilldown"  # Drill down analysis
    ANOMALY = "anomaly"  # Anomaly detection
    PYTHON = "python"  # Python analysis
    SYNTHESIS = "synthesis"  # Synthesis tools


@dataclass
class ToolSignature:
    """Signature for a tool."""

    name: str
    description: str
    category: ToolCategory
    parameters: dict[str, Any]  # Parameter schema
    returns: dict[str, Any]  # Return schema
    requires_schema: bool = False  # Whether tool needs schema info
    timeout_seconds: int = 60
    cost_weight: float = 1.0  # Relative cost for budgeting


class ToolExecutionContext(BaseModel):
    """Context for tool execution."""

    model_config = ConfigDict(extra="allow")

    task_id: str = Field(default="")
    step_id: str = Field(default="")
    domain: str = Field(default="")
    user_roles: list[str] = Field(default_factory=list)
    schema_info: dict[str, Any] = Field(default_factory=dict)
    semantic_package: dict[str, Any] = Field(default_factory=dict)
    intent: dict[str, Any] = Field(default_factory=dict)
    budget_remaining_ms: int = Field(default=60000)


@dataclass
class ToolResult:
    """Result from tool execution."""

    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)  # Observations to record

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


# =============================================================================
# Tool Registry
# =============================================================================


class ToolRegistry:
    """Registry for available tools.

    This registry:
    - Stores tool definitions
    - Manages tool handlers
    - Selects tools for tasks
    - Executes tools with context
    """

    def __init__(self):
        """Initialize tool registry."""
        self._tools: dict[str, ToolSignature] = {}
        self._handlers: dict[str, Callable] = {}
        self._category_tools: dict[ToolCategory, list[str]] = {}

    def register(
        self,
        name: str,
        signature: ToolSignature,
        handler: Callable,
    ) -> None:
        """Register a tool.

        Args:
            name: Tool name
            signature: Tool signature
            handler: Async function to execute
        """
        self._tools[name] = signature
        self._handlers[name] = handler
        self._category_tools.setdefault(signature.category, []).append(name)

        logger.info(f"Registered tool: {name}", extra={"category": signature.category.value})

    def get(self, name: str) -> ToolSignature | None:
        """Get tool signature.

        Args:
            name: Tool name

        Returns:
            Tool signature
        """
        return self._tools.get(name)

    def get_by_category(self, category: ToolCategory) -> list[ToolSignature]:
        """Get tools by category.

        Args:
            category: Tool category

        Returns:
            List of tool signatures
        """
        tool_names = self._category_tools.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_all(self) -> list[ToolSignature]:
        """List all registered tools.

        Returns:
            List of tool signatures
        """
        return list(self._tools.values())

    async def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        """Execute a tool.

        Args:
            tool_name: Tool to execute
            parameters: Tool parameters
            context: Execution context

        Returns:
            Tool result
        """
        start_time = datetime.now()
        signature = self._tools.get(tool_name)
        handler = self._handlers.get(tool_name)

        if not signature or not handler:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}",
            )

        with trace_span(f"tool.{tool_name}", {
            "task_id": context.task_id,
            "step_id": context.step_id,
            "category": signature.category.value,
        }):
            try:
                result = await handler(parameters, context)
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    data=result,
                    execution_time_ms=execution_time_ms,
                    metadata={
                        "category": signature.category.value,
                        "cost_weight": signature.cost_weight,
                    },
                )

            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name} - {e}")
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=str(e),
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                )

    def select_tools(
        self,
        intent: dict[str, Any],
        analysis_type: str,
    ) -> list[str]:
        """Select appropriate tools for an analysis.

        Args:
            intent: Resolved intent
            analysis_type: Type of analysis

        Returns:
            List of tool names
        """
        selected = []

        # Always include NL2SQL for data retrieval
        if self._tools.get("nl2sql_query"):
            selected.append("nl2sql_query")

        # Add analysis tools based on type
        tool_mapping = {
            "trend": ["trend_analysis"],
            "comparison": ["period_comparison"],
            "contribution": ["contribution_analysis"],
            "variance": ["variance_analysis"],
            "drilldown": ["drilldown"],
            "anomaly": ["anomaly_detection"],
            "pvm": ["price_volume_mix"],
        }

        for tool_name in tool_mapping.get(analysis_type, []):
            if self._tools.get(tool_name):
                selected.append(tool_name)

        return selected


# =============================================================================
# Analytics Tool Implementations
# =============================================================================


class NL2SQLTool:
    """Natural Language to SQL tool."""

    SIGNATURE = ToolSignature(
        name="nl2sql_query",
        description="Execute a natural language query against the database",
        category=ToolCategory.NL2SQL,
        parameters={
            "question": {"type": "string", "required": True},
            "parameters": {"type": "object", "required": False},
        },
        returns={
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
                "results": {"type": "array"},
                "row_count": {"type": "integer"},
            },
        },
        requires_schema=True,
        cost_weight=1.0,
    )

    def __init__(self, nl2sql_service: Any | None = None):
        """Initialize NL2SQL tool.

        Args:
            nl2sql_service: NL2SQL service instance
        """
        self._service = nl2sql_service

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute NL2SQL query.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Query results
        """
        question = parameters.get("question", "")

        if not self._service:
            # Mock response for testing
            return {
                "sql": f"-- Mock SQL for: {question}",
                "results": [{"mock": "data"}],
                "row_count": 1,
            }

        # Use actual NL2SQL service
        from eiw.nl2sql.service import NL2SQLRequest, QueryLane

        request = NL2SQLRequest(
            question=question,
            domain=context.domain,
            parameters=parameters.get("parameters", {}),
        )

        result = await self._service.execute(request)

        return {
            "sql": result.generated_sql or "",
            "results": result.rows or [],
            "row_count": len(result.rows) if result.rows else 0,
            "execution_time_ms": result.pipeline_duration_ms,
        }


class TrendAnalysisTool:
    """Trend analysis tool."""

    SIGNATURE = ToolSignature(
        name="trend_analysis",
        description="Analyze trends over time periods",
        category=ToolCategory.TREND,
        parameters={
            "metric": {"type": "string", "required": True},
            "time_granularity": {"type": "string", "required": True},
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
            "dimensions": {"type": "array", "required": False},
        },
        returns={
            "type": "object",
            "properties": {
                "trend": {"type": "string"},
                "direction": {"type": "string"},
                "magnitude": {"type": "number"},
                "data_points": {"type": "array"},
            },
        },
        cost_weight=0.5,
    )

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute trend analysis.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Trend analysis results
        """
        metric = parameters.get("metric", "")
        granularity = parameters.get("time_granularity", "day")
        start = parameters.get("start_date", "")
        end = parameters.get("end_date", "")

        # Mock trend analysis
        return {
            "metric": metric,
            "granularity": granularity,
            "period": f"{start} to {end}",
            "trend": "increasing",
            "direction": "up",
            "magnitude": 0.15,  # 15% increase
            "data_points": [
                {"date": start, "value": 100},
                {"date": end, "value": 115},
            ],
            "observations": [
                f"{metric} showed an upward trend",
                "Growth rate: 15% over the period",
            ],
        }


class PeriodComparisonTool:
    """Period comparison tool."""

    SIGNATURE = ToolSignature(
        name="period_comparison",
        description="Compare metrics between two time periods",
        category=ToolCategory.COMPARISON,
        parameters={
            "metric": {"type": "string", "required": True},
            "current_period_start": {"type": "string", "required": True},
            "current_period_end": {"type": "string", "required": True},
            "comparison_period_start": {"type": "string", "required": True},
            "comparison_period_end": {"type": "string", "required": True},
            "dimensions": {"type": "array", "required": False},
        },
        returns={
            "type": "object",
            "properties": {
                "current_value": {"type": "number"},
                "comparison_value": {"type": "number"},
                "change": {"type": "number"},
                "change_percent": {"type": "number"},
            },
        },
        cost_weight=0.5,
    )

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute period comparison.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Comparison results
        """
        metric = parameters.get("metric", "")
        current = parameters.get("current_period_end", "")
        comparison = parameters.get("comparison_period_end", "")

        # Mock comparison
        return {
            "metric": metric,
            "current_period": f"{parameters.get('current_period_start')} to {current}",
            "comparison_period": f"{parameters.get('comparison_period_start')} to {comparison}",
            "current_value": 1250.50,
            "comparison_value": 1100.00,
            "change": 150.50,
            "change_percent": 13.68,
            "observations": [
                f"{metric} increased by 13.68% compared to previous period",
                "Absolute change: +150.50",
            ],
        }


class ContributionAnalysisTool:
    """Contribution analysis tool."""

    SIGNATURE = ToolSignature(
        name="contribution_analysis",
        description="Analyze contribution of segments to total",
        category=ToolCategory.CONTRIBUTION,
        parameters={
            "metric": {"type": "string", "required": True},
            "dimension": {"type": "string", "required": True},
            "period": {"type": "string", "required": True},
            "top_n": {"type": "integer", "required": False},
        },
        returns={
            "type": "object",
            "properties": {
                "total": {"type": "number"},
                "contributions": {"type": "array"},
            },
        },
        cost_weight=0.6,
    )

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute contribution analysis.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Contribution results
        """
        metric = parameters.get("metric", "")
        dimension = parameters.get("dimension", "")

        # Mock contribution analysis
        return {
            "metric": metric,
            "dimension": dimension,
            "period": parameters.get("period", ""),
            "total": 50000.00,
            "contributions": [
                {"segment": "Segment A", "value": 20000.00, "percent": 40.0},
                {"segment": "Segment B", "value": 15000.00, "percent": 30.0},
                {"segment": "Segment C", "value": 10000.00, "percent": 20.0},
                {"segment": "Other", "value": 5000.00, "percent": 10.0},
            ],
            "observations": [
                f"{dimension} 'Segment A' is the largest contributor at 40%",
                "Top 3 segments account for 90% of total",
            ],
        }


class PriceVolumeMixTool:
    """Price Volume Mix analysis tool."""

    SIGNATURE = ToolSignature(
        name="price_volume_mix",
        description="Price Volume Mix decomposition analysis",
        category=ToolCategory.PVM,
        parameters={
            "metric": {"type": "string", "required": True},
            "current_period": {"type": "string", "required": True},
            "comparison_period": {"type": "string", "required": True},
            "products": {"type": "array", "required": False},
        },
        returns={
            "type": "object",
            "properties": {
                "total_change": {"type": "number"},
                "price_effect": {"type": "number"},
                "volume_effect": {"type": "number"},
                "mix_effect": {"type": "number"},
            },
        },
        cost_weight=0.8,
    )

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute PVM analysis.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            PVM results
        """
        return {
            "metric": parameters.get("metric", ""),
            "current_period": parameters.get("current_period", ""),
            "comparison_period": parameters.get("comparison_period", ""),
            "total_change": 1500.00,
            "price_effect": 800.00,
            "volume_effect": 500.00,
            "mix_effect": 200.00,
            "breakdown": {
                "price_effect_pct": 53.3,
                "volume_effect_pct": 33.3,
                "mix_effect_pct": 13.3,
            },
            "observations": [
                "Price effect (+53.3%) is the main driver of growth",
                "Volume contributed 33.3% of the change",
            ],
        }


class VarianceAnalysisTool:
    """Variance analysis tool."""

    SIGNATURE = ToolSignature(
        name="variance_analysis",
        description="Budget vs actual variance analysis",
        category=ToolCategory.VARIANCE,
        parameters={
            "metric": {"type": "string", "required": True},
            "actual_value": {"type": "number", "required": True},
            "budget_value": {"type": "number", "required": True},
            "dimensions": {"type": "array", "required": False},
        },
        returns={
            "type": "object",
            "properties": {
                "variance": {"type": "number"},
                "variance_percent": {"type": "number"},
                "favorable": {"type": "boolean"},
            },
        },
        cost_weight=0.4,
    )

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute variance analysis.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Variance results
        """
        actual = parameters.get("actual_value", 0)
        budget = parameters.get("budget_value", 0)
        variance = actual - budget
        variance_pct = (variance / budget * 100) if budget else 0

        return {
            "metric": parameters.get("metric", ""),
            "actual": actual,
            "budget": budget,
            "variance": variance,
            "variance_percent": variance_pct,
            "favorable": variance >= 0 if "revenue" in parameters.get("metric", "").lower() else variance <= 0,
            "observations": [
                f"Variance: {variance:+.2f} ({variance_pct:+.1f}%)",
                "Favorable" if variance >= 0 else "Unfavorable",
            ],
        }


class DrilldownTool:
    """Drilldown analysis tool."""

    SIGNATURE = ToolSignature(
        name="drilldown",
        description="Drill down into data dimensions",
        category=ToolCategory.DRILLDOWN,
        parameters={
            "metric": {"type": "string", "required": True},
            "from_dimension": {"type": "string", "required": True},
            "to_dimension": {"type": "string", "required": True},
            "filter_value": {"type": "string", "required": True},
            "period": {"type": "string", "required": True},
        },
        returns={
            "type": "object",
            "properties": {
                "rows": {"type": "array"},
            },
        },
        cost_weight=0.3,
    )

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute drilldown.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Drilldown results
        """
        return {
            "metric": parameters.get("metric", ""),
            "drilldown_path": f"{parameters.get('from_dimension')} -> {parameters.get('to_dimension')}",
            "filter": parameters.get("filter_value", ""),
            "period": parameters.get("period", ""),
            "rows": [
                {"sub_segment": "Sub-A", "value": 5000.00},
                {"sub_segment": "Sub-B", "value": 3000.00},
                {"sub_segment": "Sub-C", "value": 2000.00},
            ],
            "observations": [
                f"Drilled into {parameters.get('to_dimension')} for {parameters.get('filter_value')}",
            ],
        }


class AnomalyDetectionTool:
    """Anomaly detection tool."""

    SIGNATURE = ToolSignature(
        name="anomaly_detection",
        description="Detect anomalies in time series data",
        category=ToolCategory.ANOMALY,
        parameters={
            "metric": {"type": "string", "required": True},
            "period": {"type": "string", "required": True},
            "sensitivity": {"type": "number", "required": False},
        },
        returns={
            "type": "object",
            "properties": {
                "anomalies": {"type": "array"},
            },
        },
        cost_weight=0.7,
    )

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute anomaly detection.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Anomaly results
        """
        return {
            "metric": parameters.get("metric", ""),
            "period": parameters.get("period", ""),
            "sensitivity": parameters.get("sensitivity", 2.0),
            "anomalies": [
                {
                    "date": "2024-03-15",
                    "value": 2500.00,
                    "expected": 1000.00,
                    "deviation": 150.0,
                    "type": "spike",
                },
            ],
            "observations": [
                "Detected 1 anomaly: spike on 2024-03-15 (150% above expected)",
            ],
        }


# =============================================================================
# Python Analysis Tool (Sandboxed)
# =============================================================================


class PythonAnalysisTool:
    """Bounded Python analysis tool with sandbox."""

    SIGNATURE = ToolSignature(
        name="python_analysis",
        description="Execute bounded Python code for custom analysis",
        category=ToolCategory.PYTHON,
        parameters={
            "code": {"type": "string", "required": True},
            "data": {"type": "any", "required": False},
        },
        returns={
            "type": "object",
            "properties": {
                "output": {"type": "string"},
                "error": {"type": "string"},
            },
        },
        timeout_seconds=30,
        cost_weight=2.0,
    )

    # Allowed imports for sandbox
    ALLOWED_IMPORTS: set[str] = {
        "math", "statistics", "datetime", "date", "timedelta",
        "json", "re", "collections", "functools", "itertools",
        "numpy",  # Optional - available if installed
    }

    # Blocked patterns
    BLOCKED_PATTERNS = [
        "import os", "import sys", "import subprocess",
        "import socket", "import requests", "import urllib",
        "open(", "file", "exec(", "eval(",
        "__import__", "breakpoint", "input(",
    ]

    def __init__(self, sandbox_enabled: bool = True):
        """Initialize Python tool.

        Args:
            sandbox_enabled: Whether to enable sandbox
        """
        self._sandbox_enabled = sandbox_enabled

    async def execute(
        self,
        parameters: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute Python code.

        Args:
            parameters: Tool parameters
            context: Execution context

        Returns:
            Execution results
        """
        code = parameters.get("code", "")
        data = parameters.get("data", {})

        if self._sandbox_enabled:
            return self._execute_sandboxed(code, data)
        else:
            return self._execute_unsafe(code, data)

    def _execute_sandboxed(self, code: str, data: Any) -> dict[str, Any]:
        """Execute code in sandbox.

        Args:
            code: Python code
            data: Input data

        Returns:
            Results
        """
        import io
        import sys

        # Security check
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in code:
                return {
                    "output": "",
                    "error": f"Blocked pattern detected: {pattern}",
                }

        # Capture output
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Build context with allowed imports
            allowed_modules = {}
            for module_name in self.ALLOWED_IMPORTS:
                try:
                    # Import module if available
                    mod = __import__(module_name)
                    allowed_modules[module_name] = mod
                except ImportError:
                    pass

            # Build restricted builtins (allow only safe operations)
            safe_builtins = {
                "__import__": __import__,  # Required for import statements
                "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
                "chr": chr, "dict": dict, "dir": dir, "divmod": divmod,
                "enumerate": enumerate, "filter": filter, "float": float,
                "format": format, "frozenset": frozenset, "hash": hash,
                "hex": hex, "int": int, "isinstance": isinstance,
                "issubclass": issubclass, "iter": iter, "len": len,
                "list": list, "map": map, "max": max, "min": min,
                "next": next, "object": object, "oct": oct, "ord": ord,
                "pow": pow, "range": range, "repr": repr, "reversed": reversed,
                "round": round, "set": set, "slice": slice, "sorted": sorted,
                "str": str, "sum": sum, "tuple": tuple, "zip": zip,
                "type": type, "vars": vars, "print": print,
            }

            context_locals = {
                "data": data,
                "result": None,
            }
            context_globals = {
                "__builtins__": safe_builtins,
                **allowed_modules,
            }

            # Execute
            exec(code, context_globals, context_locals)

            output = sys.stdout.getvalue()
            result = context_locals.get("result")

            return {
                "output": output or str(result) if result is not None else output,
                "error": None,
                "result": result,
            }

        except Exception as e:
            return {
                "output": sys.stdout.getvalue(),
                "error": str(e),
            }

        finally:
            sys.stdout = old_stdout

    def _execute_unsafe(self, code: str, data: Any) -> dict[str, Any]:
        """Execute code without sandbox (use with caution)."""
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Build context with allowed imports
            allowed_modules = {}
            for module_name in self.ALLOWED_IMPORTS:
                try:
                    mod = __import__(module_name)
                    allowed_modules[module_name] = mod
                except ImportError:
                    pass

            context_locals = {"data": data, "result": None, **allowed_modules}
            context_globals = {"__builtins__": __builtins__, **allowed_modules}
            exec(code, context_globals, context_locals)
            output = sys.stdout.getvalue()
            result = context_locals.get("result")
            return {"output": output or str(result) if result is not None else output, "error": None, "result": result}
        except Exception as e:
            return {"output": sys.stdout.getvalue(), "error": str(e)}
        finally:
            sys.stdout = old_stdout


# =============================================================================
# Metric Explain Tool
# =============================================================================


class MetricExplainTool:
    """Tool for explaining metric definitions and calculations."""

    SIGNATURE = ToolSignature(
        name="metric_explain",
        description="Explain a metric's definition, formula, and business rules",
        category=ToolCategory.SYNTHESIS,
        parameters={
            "type": "object",
            "properties": {
                "metric_id": {"type": "string", "description": "Metric identifier"},
                "include_formula": {"type": "boolean", "description": "Include calculation formula", "default": True},
                "include_examples": {"type": "boolean", "description": "Include SQL examples", "default": True},
            },
            "required": ["metric_id"],
        },
        returns={
            "type": "object",
            "properties": {
                "metric_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "formula": {"type": "string"},
                "unit": {"type": "string"},
                "valid_grains": {"type": "array"},
                "supported_dimensions": {"type": "array"},
                "examples": {"type": "array"},
            },
        },
    )

    def __init__(self, semantic_package: dict[str, Any] | None = None):
        self._semantic_package = semantic_package or {}

    async def execute(
        self,
        params: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute metric explain.

        Args:
            params: Tool parameters
            context: Execution context

        Returns:
            Metric explanation
        """
        metric_id = params.get("metric_id")
        include_formula = params.get("include_formula", True)
        include_examples = params.get("include_examples", True)

        # Get metric from semantic package
        metric = self._get_metric(metric_id)
        if not metric:
            return {"error": f"Metric not found: {metric_id}"}

        result = {
            "metric_id": metric.get("id", metric_id),
            "name": metric.get("name", metric_id),
            "description": metric.get("description", ""),
        }

        if include_formula:
            result["formula"] = metric.get("formula", metric.get("semantic_expression", ""))
            result["unit"] = metric.get("unit", "count")

        if "valid_grains" in metric:
            result["valid_grains"] = metric["valid_grains"]
        if "supported_dimensions" in metric or "dimensions" in metric:
            result["supported_dimensions"] = metric.get("supported_dimensions", metric.get("dimensions", []))

        if include_examples and "examples" in metric:
            result["examples"] = metric["examples"]

        return result

    def _get_metric(self, metric_id: str) -> dict[str, Any] | None:
        """Get metric definition from semantic package."""
        metrics = self._semantic_package.get("metrics", [])
        for metric in metrics:
            if metric.get("id") == metric_id:
                return metric
        return None


# =============================================================================
# Knowledge Search Tool
# =============================================================================


class KnowledgeSearchTool:
    """Tool for searching the knowledge base."""

    SIGNATURE = ToolSignature(
        name="knowledge_search",
        description="Search the knowledge base for metric definitions, business rules, and SQL examples",
        category=ToolCategory.SYNTHESIS,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "source_type": {
                    "type": "string",
                    "description": "Filter by source type",
                    "enum": ["glossary", "metric_definition", "schema", "sql_example", "all"],
                    "default": "all",
                },
                "limit": {"type": "integer", "description": "Max results", "default": 5},
            },
            "required": ["query"],
        },
        returns={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "results": {"type": "array"},
                "total": {"type": "integer"},
            },
        },
    )

    def __init__(self, knowledge_base: dict[str, Any] | None = None):
        self._knowledge_base = knowledge_base or {}

    async def execute(
        self,
        params: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute knowledge search.

        Args:
            params: Tool parameters
            context: Execution context

        Returns:
            Search results
        """
        query = params.get("query", "")
        source_type = params.get("source_type", "all")
        limit = params.get("limit", 5)

        # Search through knowledge base
        results = []
        search_sources = self._get_search_sources(source_type)

        for source_name, source_data in search_sources.items():
            matches = self._search_source(query, source_data)
            for match in matches[:limit]:
                results.append({
                    "source": source_name,
                    "source_type": source_data.get("type", "unknown"),
                    "title": match.get("title", ""),
                    "content": match.get("content", ""),
                    "relevance": match.get("relevance", 0.5),
                })

        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        return {
            "query": query,
            "results": results[:limit],
            "total": len(results),
        }

    def _get_search_sources(self, source_type: str) -> dict[str, Any]:
        """Get knowledge sources to search."""
        if source_type == "all":
            return self._knowledge_base
        # Filter by type
        return {k: v for k, v in self._knowledge_base.items() if v.get("type") == source_type}

    def _search_source(self, query: str, source_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Search a single source."""
        query_lower = query.lower()
        results = []

        items = source_data.get("items", [])
        for item in items:
            # Simple text matching
            content = str(item.get("content", "")).lower()
            title = str(item.get("title", "")).lower()
            if query_lower in content or query_lower in title:
                results.append({
                    **item,
                    "relevance": 0.8 if query_lower in title else 0.6,
                })

        return results


# =============================================================================
# Chart Generate Tool
# =============================================================================


class ChartGenerateTool:
    """Tool for generating chart specifications from observations."""

    SIGNATURE = ToolSignature(
        name="chart_generate",
        description="Generate chart specifications from analysis observations",
        category=ToolCategory.SYNTHESIS,
        parameters={
            "type": "object",
            "properties": {
                "observations": {
                    "type": "array",
                    "description": "Observations to visualize",
                    "items": {"type": "object"},
                },
                "chart_type": {
                    "type": "string",
                    "description": "Chart type",
                    "enum": ["line", "bar", "pie", "scatter", "area", "auto"],
                    "default": "auto",
                },
                "title": {"type": "string", "description": "Chart title"},
            },
            "required": ["observations"],
        },
        returns={
            "type": "object",
            "properties": {
                "chart_spec": {"type": "object"},
                "chart_type": {"type": "string"},
                "data_points": {"type": "integer"},
            },
        },
    )

    async def execute(
        self,
        params: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute chart generation.

        Args:
            params: Tool parameters
            context: Execution context

        Returns:
            Chart specification
        """
        observations = params.get("observations", [])
        chart_type = params.get("chart_type", "auto")
        title = params.get("title", "Analysis Chart")

        # Validate observations
        if not observations:
            return {"error": "No observations provided for chart"}

        # Determine chart type from data if auto
        if chart_type == "auto":
            chart_type = self._infer_chart_type(observations)

        # Build chart spec
        chart_spec = self._build_chart_spec(observations, chart_type, title)

        return {
            "chart_spec": chart_spec,
            "chart_type": chart_type,
            "data_points": len(observations),
        }

    def _infer_chart_type(self, observations: list[dict[str, Any]]) -> str:
        """Infer chart type from observation structure."""
        if len(observations) > 1 and "period" in str(observations[0]):
            return "line"
        if len(observations) > 0 and "category" in observations[0]:
            return "bar"
        return "bar"

    def _build_chart_spec(
        self,
        observations: list[dict[str, Any]],
        chart_type: str,
        title: str,
    ) -> dict[str, Any]:
        """Build chart specification."""
        return {
            "type": chart_type,
            "title": title,
            "data": observations,
            "encoding": {
                "x": {"field": self._get_x_field(observations)},
                "y": {"field": self._get_y_field(observations)},
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": True,
            },
        }

    def _get_x_field(self, observations: list[dict[str, Any]]) -> str:
        """Get x-axis field from observations."""
        for field in ["period", "date", "category", "dimension", "name"]:
            if field in observations[0]:
                return field
        return "label"

    def _get_y_field(self, observations: list[dict[str, Any]]) -> str:
        """Get y-axis field from observations."""
        for field in ["value", "amount", "count", "result"]:
            if field in observations[0]:
                return field
        return "value"


# =============================================================================
# Report Generate Tool
# =============================================================================


class ReportGenerateTool:
    """Tool for generating structured analysis reports."""

    SIGNATURE = ToolSignature(
        name="report_generate",
        description="Generate a structured analysis report from observations and claims",
        category=ToolCategory.SYNTHESIS,
        parameters={
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Original business question"},
                "observations": {"type": "array", "description": "Analysis observations"},
                "claims": {"type": "array", "description": "Verified claims"},
                "limitations": {"type": "array", "description": "Known limitations"},
                "recommendations": {"type": "array", "description": "Recommended next steps"},
            },
            "required": ["question", "observations"],
        },
        returns={
            "type": "object",
            "properties": {
                "report": {"type": "object"},
                "sections": {"type": "array"},
            },
        },
    )

    async def execute(
        self,
        params: dict[str, Any],
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        """Execute report generation.

        Args:
            params: Tool parameters
            context: Execution context

        Returns:
            Generated report
        """
        question = params.get("question", "")
        observations = params.get("observations", [])
        claims = params.get("claims", [])
        limitations = params.get("limitations", [])
        recommendations = params.get("recommendations", [])

        # Build report sections
        sections = []

        # Executive Summary
        sections.append({
            "type": "executive_summary",
            "title": "Executive Summary",
            "content": self._generate_summary(observations, claims),
        })

        # Metrics
        sections.append({
            "type": "metrics",
            "title": "Key Metrics",
            "content": self._generate_metrics(observations),
        })

        # Findings
        if claims:
            sections.append({
                "type": "findings",
                "title": "Key Findings",
                "content": self._generate_findings(claims),
            })

        # Evidence
        sections.append({
            "type": "evidence",
            "title": "Evidence",
            "content": self._generate_evidence(observations),
        })

        # Limitations
        if limitations:
            sections.append({
                "type": "limitations",
                "title": "Limitations",
                "content": limitations,
            })

        # Recommendations
        if recommendations:
            sections.append({
                "type": "recommendations",
                "title": "Recommendations",
                "content": recommendations,
            })

        report = {
            "question": question,
            "sections": sections,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "observation_count": len(observations),
                "claim_count": len(claims),
            },
        }

        return {
            "report": report,
            "sections": [s["type"] for s in sections],
        }

    def _generate_summary(self, observations: list[dict], claims: list[dict]) -> str:
        """Generate executive summary."""
        if not observations:
            return "No observations available."
        return f"Analysis of {len(observations)} observations yielded {len(claims)} verified claims."

    def _generate_metrics(self, observations: list[dict]) -> list[dict]:
        """Generate metrics section."""
        metrics = []
        for obs in observations:
            if "value" in obs or "result" in obs:
                metrics.append({
                    "name": obs.get("name", obs.get("observation_id", "metric")),
                    "value": obs.get("value", obs.get("result", "N/A")),
                })
        return metrics

    def _generate_findings(self, claims: list[dict]) -> list[str]:
        """Generate findings from claims."""
        return [claim.get("statement", claim.get("content", "")) for claim in claims if claim]

    def _generate_evidence(self, observations: list[dict]) -> list[dict]:
        """Generate evidence section."""
        return [
            {
                "observation_id": obs.get("observation_id", f"obs_{i}"),
                "content": obs.get("content", obs.get("result", "")),
            }
            for i, obs in enumerate(observations)
        ]


# =============================================================================
# Tool Registry Factory
# =============================================================================


def create_tool_registry(nl2sql_service: Any | None = None) -> ToolRegistry:
    """Create and populate tool registry.

    Args:
        nl2sql_service: Optional NL2SQL service

    Returns:
        Populated tool registry
    """
    registry = ToolRegistry()

    # Create tool instances
    nl2sql_tool = NL2SQLTool(nl2sql_service)
    trend_tool = TrendAnalysisTool()
    comparison_tool = PeriodComparisonTool()
    contribution_tool = ContributionAnalysisTool()
    pvm_tool = PriceVolumeMixTool()
    variance_tool = VarianceAnalysisTool()
    drilldown_tool = DrilldownTool()
    anomaly_tool = AnomalyDetectionTool()
    python_tool = PythonAnalysisTool()

    # Register tools
    registry.register(
        NL2SQLTool.SIGNATURE.name,
        NL2SQLTool.SIGNATURE,
        lambda p, c: nl2sql_tool.execute(p, c),
    )
    registry.register(
        TrendAnalysisTool.SIGNATURE.name,
        TrendAnalysisTool.SIGNATURE,
        lambda p, c: trend_tool.execute(p, c),
    )
    registry.register(
        PeriodComparisonTool.SIGNATURE.name,
        PeriodComparisonTool.SIGNATURE,
        lambda p, c: comparison_tool.execute(p, c),
    )
    registry.register(
        ContributionAnalysisTool.SIGNATURE.name,
        ContributionAnalysisTool.SIGNATURE,
        lambda p, c: contribution_tool.execute(p, c),
    )
    registry.register(
        PriceVolumeMixTool.SIGNATURE.name,
        PriceVolumeMixTool.SIGNATURE,
        lambda p, c: pvm_tool.execute(p, c),
    )
    registry.register(
        VarianceAnalysisTool.SIGNATURE.name,
        VarianceAnalysisTool.SIGNATURE,
        lambda p, c: variance_tool.execute(p, c),
    )
    registry.register(
        DrilldownTool.SIGNATURE.name,
        DrilldownTool.SIGNATURE,
        lambda p, c: drilldown_tool.execute(p, c),
    )
    registry.register(
        AnomalyDetectionTool.SIGNATURE.name,
        AnomalyDetectionTool.SIGNATURE,
        lambda p, c: anomaly_tool.execute(p, c),
    )
    registry.register(
        PythonAnalysisTool.SIGNATURE.name,
        PythonAnalysisTool.SIGNATURE,
        lambda p, c: python_tool.execute(p, c),
    )

    # Register new tools
    metric_explain_tool = MetricExplainTool()
    knowledge_search_tool = KnowledgeSearchTool()
    chart_generate_tool = ChartGenerateTool()
    report_generate_tool = ReportGenerateTool()

    registry.register(
        MetricExplainTool.SIGNATURE.name,
        MetricExplainTool.SIGNATURE,
        lambda p, c: metric_explain_tool.execute(p, c),
    )
    registry.register(
        KnowledgeSearchTool.SIGNATURE.name,
        KnowledgeSearchTool.SIGNATURE,
        lambda p, c: knowledge_search_tool.execute(p, c),
    )
    registry.register(
        ChartGenerateTool.SIGNATURE.name,
        ChartGenerateTool.SIGNATURE,
        lambda p, c: chart_generate_tool.execute(p, c),
    )
    registry.register(
        ReportGenerateTool.SIGNATURE.name,
        ReportGenerateTool.SIGNATURE,
        lambda p, c: report_generate_tool.execute(p, c),
    )

    return registry
