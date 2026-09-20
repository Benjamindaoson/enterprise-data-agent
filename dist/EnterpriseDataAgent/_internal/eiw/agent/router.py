"""Tool Router for Enterprise Data Agent.

Routes analysis tasks to appropriate analytical tools based on:
- Resolved intent
- Available metrics/dimensions
- User permissions
- Data availability
- Budget constraints
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolCategory(Enum):
    """Categories of analytical tools."""

    METRIC = "metric"           # KPI/metric queries
    NL2SQL = "nl2sql"           # Ad-hoc SQL queries
    KNOWLEDGE = "knowledge"     # RAG/knowledge retrieval
    ANALYTICS = "analytics"     # Trend, attribution, etc.
    PYTHON = "python"           # Statistical analysis
    REPORT = "report"           # Report generation
    CHART = "chart"             # Visualization


@dataclass
class ToolSignature:
    """Signature of an analytical tool."""

    name: str
    category: ToolCategory
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_metrics: list[str] = field(default_factory=list)
    required_dimensions: list[str] = field(default_factory=list)
    supports_multi_step: bool = False
    timeout_seconds: int = 30
    max_rows: int = 10000
    cost_weight: float = 1.0  # Relative cost for budget tracking


@dataclass
class RoutingDecision:
    """Result of tool routing decision."""

    primary_tool: str
    fallback_tools: list[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 1.0
    estimated_duration_seconds: int = 30
    requires_nl2sql: bool = False
    semantic_path: bool = False


class ToolRouter:
    """Routes analysis requests to appropriate tools.

    This is the core routing logic for the Enterprise Data Agent's
    dual-query-channel architecture:
    - Governed Metric Query: For known KPIs/routine BI
    - Governed NL2SQL: For long-tail ad-hoc queries
    """

    # Tool registry
    TOOLS: dict[str, ToolSignature] = {
        # Metric Query Tools
        "metric_query": ToolSignature(
            name="metric_query",
            category=ToolCategory.METRIC,
            description="Query pre-defined KPIs and metrics from the semantic layer",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_ids": {"type": "array", "items": {"type": "string"}},
                    "dimensions": {"type": "array", "items": {"type": "string"}},
                    "filters": {"type": "object"},
                    "period": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string"},
                            "end": {"type": "string"},
                        },
                    },
                },
                "required": ["metric_ids"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "metadata": {"type": "object"},
                },
            },
            required_metrics=["*"],  # All metrics in semantic layer
            supports_multi_step=True,
            cost_weight=1.0,
        ),
        # NL2SQL Tools
        "nl2sql_query": ToolSignature(
            name="nl2sql_query",
            category=ToolCategory.NL2SQL,
            description="Execute ad-hoc SQL queries generated from natural language",
            input_schema={
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["question"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "results": {"type": "array"},
                    "execution_time_ms": {"type": "number"},
                },
            },
            supports_multi_step=True,
            timeout_seconds=60,
            cost_weight=2.0,
        ),
        "nl2sql_explain": ToolSignature(
            name="nl2sql_explain",
            category=ToolCategory.NL2SQL,
            description="Explain a generated SQL query in business terms",
            input_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                },
                "required": ["sql"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "explanation": {"type": "string"},
                    "tables_used": {"type": "array"},
                    "metrics_calculated": {"type": "array"},
                },
            },
            cost_weight=0.5,
        ),
        # Analytics Tools
        "trend_analysis": ToolSignature(
            name="trend_analysis",
            category=ToolCategory.ANALYTICS,
            description="Analyze time-series trends for metrics",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_id": {"type": "string"},
                    "period": {"type": "object"},
                    "granularity": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly"]},
                },
                "required": ["metric_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "trend": {"type": "string"},
                    "growth_rate": {"type": "number"},
                    "data_points": {"type": "array"},
                },
            },
            required_metrics=["*"],
            cost_weight=1.5,
        ),
        "period_compare": ToolSignature(
            name="period_compare",
            category=ToolCategory.ANALYTICS,
            description="Compare metrics across time periods (MoM, YoY)",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_ids": {"type": "array"},
                    "current_period": {"type": "object"},
                    "comparison_period": {"type": "object"},
                },
                "required": ["metric_ids"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "comparisons": {"type": "array"},
                    "changes": {"type": "object"},
                },
            },
            cost_weight=1.5,
        ),
        "contribution_analysis": ToolSignature(
            name="contribution_analysis",
            category=ToolCategory.ANALYTICS,
            description="Rank contributors to a metric change",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_id": {"type": "string"},
                    "dimension": {"type": "string"},
                    "current_period": {"type": "object"},
                    "comparison_period": {"type": "object"},
                },
                "required": ["metric_id", "dimension"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "contributors": {"type": "array"},
                    "total_change": {"type": "number"},
                },
            },
            required_dimensions=["*"],
            cost_weight=2.0,
        ),
        "pvm_analysis": ToolSignature(
            name="pvm_analysis",
            category=ToolCategory.ANALYTICS,
            description="Price-Volume-Mix decomposition of revenue change",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_id": {"type": "string", "default": "revenue"},
                    "current_period": {"type": "object"},
                    "comparison_period": {"type": "object"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "volume_effect": {"type": "number"},
                    "price_effect": {"type": "number"},
                    "mix_residual": {"type": "number"},
                    "total_change": {"type": "number"},
                },
            },
            cost_weight=2.5,
        ),
        "variance_analysis": ToolSignature(
            name="variance_analysis",
            category=ToolCategory.ANALYTICS,
            description="Budget vs Actual variance analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_id": {"type": "string"},
                    "period": {"type": "object"},
                    "budget_values": {"type": "object"},
                },
                "required": ["metric_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "variance": {"type": "number"},
                    "variance_pct": {"type": "number"},
                    "favorable": {"type": "boolean"},
                },
            },
            cost_weight=2.0,
        ),
        "anomaly_detection": ToolSignature(
            name="anomaly_detection",
            category=ToolCategory.ANALYTICS,
            description="Detect anomalies and outliers in metrics",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_id": {"type": "string"},
                    "period": {"type": "object"},
                    "sensitivity": {"type": "number", "default": 2.0},
                },
                "required": ["metric_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "anomalies": {"type": "array"},
                    "threshold": {"type": "number"},
                },
            },
            cost_weight=3.0,
        ),
        "drilldown_analysis": ToolSignature(
            name="drilldown_analysis",
            category=ToolCategory.ANALYTICS,
            description="Multi-dimensional drilldown analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_id": {"type": "string"},
                    "drilldown_dimensions": {"type": "array"},
                    "period": {"type": "object"},
                },
                "required": ["metric_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "levels": {"type": "array"},
                    "data": {"type": "array"},
                },
            },
            supports_multi_step=True,
            cost_weight=3.0,
        ),
        # Knowledge Tools
        "metric_explain": ToolSignature(
            name="metric_explain",
            category=ToolCategory.KNOWLEDGE,
            description="Explain a metric definition using business glossary",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_id": {"type": "string"},
                },
                "required": ["metric_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "definition": {"type": "string"},
                    "formula": {"type": "string"},
                    "owner": {"type": "string"},
                    "dimensions": {"type": "array"},
                },
            },
            cost_weight=0.5,
        ),
        "knowledge_search": ToolSignature(
            name="knowledge_search",
            category=ToolCategory.KNOWLEDGE,
            description="Search business knowledge base for relevant context",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "number", "default": 5},
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "sources": {"type": "array"},
                },
            },
            cost_weight=1.0,
        ),
        # Python Analysis Tool
        "python_analysis": ToolSignature(
            name="python_analysis",
            category=ToolCategory.PYTHON,
            description="Execute statistical analysis in isolated sandbox",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "data": {"type": "array"},
                },
                "required": ["code"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "result": {"type": "any"},
                    "stdout": {"type": "string"},
                },
            },
            timeout_seconds=30,
            max_rows=1000,
            cost_weight=2.0,
        ),
        # Report Tools
        "report_generate": ToolSignature(
            name="report_generate",
            category=ToolCategory.REPORT,
            description="Generate formatted analysis report",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "format": {"type": "string", "enum": ["markdown", "html", "pdf"]},
                    "include_charts": {"type": "boolean"},
                },
                "required": ["task_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "report_uri": {"type": "string"},
                    "format": {"type": "string"},
                },
            },
            cost_weight=1.0,
        ),
        "chart_generate": ToolSignature(
            name="chart_generate",
            category=ToolCategory.CHART,
            description="Generate visualization from analysis results",
            input_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "array"},
                    "chart_type": {"type": "string", "enum": ["line", "bar", "pie", "scatter"]},
                    "title": {"type": "string"},
                },
                "required": ["data", "chart_type"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "chart_uri": {"type": "string"},
                    "chart_data": {"type": "string"},
                },
            },
            cost_weight=1.5,
        ),
    }

    def __init__(self) -> None:
        """Initialize tool router."""
        self.tools = self.TOOLS.copy()

    def register_tool(self, tool: ToolSignature) -> None:
        """Register a new tool in the router."""
        self.tools[tool.name] = tool

    def route(
        self,
        intent_type: str,
        metrics: list[str],
        dimensions: list[str],
        requires_nl2sql: bool = False,
        semantic_path: bool = False,
        budget_remaining: float = 1.0,
    ) -> RoutingDecision:
        """Route an analysis request to appropriate tools.

        Args:
            intent_type: Classified intent type
            metrics: Required metrics
            dimensions: Required dimensions
            requires_nl2sql: Whether NL2SQL path is needed
            semantic_path: Whether to use semantic query path
            budget_remaining: Remaining budget (0-1)

        Returns:
            RoutingDecision with primary and fallback tools
        """
        # Priority 1: If NL2SQL explicitly required, route there
        if requires_nl2sql:
            return RoutingDecision(
                primary_tool="nl2sql_query",
                fallback_tools=["metric_query"],
                reasoning="Question requires ad-hoc SQL generation for long-tail query",
                confidence=0.9,
                requires_nl2sql=True,
            )

        # Priority 2: Semantic path for known metrics
        if semantic_path and metrics:
            primary_tool = self._select_metric_tool(intent_type)
            return RoutingDecision(
                primary_tool=primary_tool,
                fallback_tools=["nl2sql_query"],
                reasoning=f"Using semantic path for known metric: {metrics[0]}",
                confidence=0.95,
                semantic_path=True,
            )

        # Priority 3: Route based on intent type
        return self._route_by_intent(intent_type, metrics, dimensions, budget_remaining)

    def _route_by_intent(
        self,
        intent_type: str,
        metrics: list[str],
        dimensions: list[str],
        budget: float,
    ) -> RoutingDecision:
        """Route based on classified intent."""
        intent_tool_map: dict[str, tuple[str, list[str]]] = {
            "metric_query": ("metric_query", []),
            "trend_analysis": ("trend_analysis", ["metric_query"]),
            "comparison": ("period_compare", ["metric_query"]),
            "contribution": ("contribution_analysis", ["metric_query"]),
            "attribution": ("nl2sql_query", ["contribution_analysis"]),
            "anomaly_detection": ("anomaly_detection", ["trend_analysis"]),
            "explain": ("metric_explain", ["knowledge_search"]),
            "budget_variance": ("variance_analysis", ["metric_query"]),
            "drilldown": ("drilldown_analysis", ["metric_query", "contribution_analysis"]),
            "nl2sql": ("nl2sql_query", []),
        }

        tool_mapping = intent_tool_map.get(intent_type, ("metric_query", []))
        primary, fallbacks = tool_mapping

        # Check if required metrics exist in semantic layer
        if primary == "metric_query" and not metrics:
            primary = "nl2sql_query"
            fallbacks = ["metric_query"]

        reasoning_map: dict[str, str] = {
            "metric_query": f"Querying metrics: {metrics}",
            "trend_analysis": "Analyzing time-series trend",
            "period_compare": "Comparing periods",
            "contribution_analysis": f"Analyzing contributions by: {dimensions}",
            "nl2sql_query": "Ad-hoc query requires SQL generation",
            "anomaly_detection": "Detecting anomalies in metric",
            "variance_analysis": "Analyzing budget variance",
            "drilldown_analysis": f"Drilling down by: {dimensions}",
        }

        return RoutingDecision(
            primary_tool=primary,
            fallback_tools=fallbacks,
            reasoning=reasoning_map.get(primary, "Standard metric query"),
            confidence=0.9,
            estimated_duration_seconds=self.tools[primary].timeout_seconds,
        )

    def _select_metric_tool(self, intent_type: str) -> str:
        """Select the appropriate metric tool for semantic path."""
        intent_to_tool: dict[str, str] = {
            "metric_query": "metric_query",
            "trend_analysis": "trend_analysis",
            "comparison": "period_compare",
            "contribution": "contribution_analysis",
            "attribution": "contribution_analysis",
            "anomaly_detection": "anomaly_detection",
            "budget_variance": "variance_analysis",
            "drilldown": "drilldown_analysis",
        }
        return intent_to_tool.get(intent_type, "metric_query")

    def get_tool(self, tool_name: str) -> ToolSignature | None:
        """Get tool signature by name."""
        return self.tools.get(tool_name)

    def list_tools_by_category(self, category: ToolCategory) -> list[ToolSignature]:
        """List all tools in a category."""
        return [t for t in self.tools.values() if t.category == category]

    def estimate_cost(
        self,
        tool_name: str,
        complexity: str = "normal",
    ) -> float:
        """Estimate the cost of executing a tool."""
        tool = self.tools.get(tool_name)
        if not tool:
            return 1.0

        complexity_multiplier = {
            "simple": 0.5,
            "normal": 1.0,
            "complex": 2.0,
        }

        return tool.cost_weight * complexity_multiplier.get(complexity, 1.0)
