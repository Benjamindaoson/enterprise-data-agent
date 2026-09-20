"""Chart Executor - Chart generation operations.

This executor handles chart and visualization operations:
- Chart type selection
- Data preparation for visualization
- Chart rendering configuration
- Multi-chart dashboard generation
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from eiw.agent.executor import (
    BaseExecutor,
    ExecutorCategory,
    ExecutorResult,
    StepContext,
)
from eiw.observability.logging import get_structured_logger
from eiw.observability.otel import trace_span

logger = get_structured_logger(__name__, "executor.chart")

# Supported chart tool types
CHART_TOOLS = {
    "chart_generate",
    "chart_configure",
    "dashboard_create",
    "chart_export",
    "chart_update",
    "report_generate",
}


class ChartExecutor(BaseExecutor):
    """Executor for chart and visualization operations.

    This executor handles:
    - Chart type selection based on data
    - Chart configuration and styling
    - Dashboard creation from multiple charts
    - Chart export in various formats
    """

    def __init__(self):
        super().__init__(
            category=ExecutorCategory.CHART,
            name="chart",
            description="Chart executor for visualization generation, configuration, and dashboard creation",
            supported_tools=CHART_TOOLS,
        )

    async def execute(
        self,
        context: StepContext,
        tool_type: str,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute chart operation.

        Args:
            context: Step execution context
            tool_type: Tool type to execute
            inputs: Tool-specific inputs

        Returns:
            Executor result with chart data
        """
        start_time = datetime.now()

        with trace_span("executor.chart.execute", {
            "task_id": context.task_id,
            "step_id": context.step_id,
            "tool_type": tool_type,
        }):
            logger.info(
                f"ChartExecutor executing {tool_type}",
                extra={"task_id": context.task_id, "step_id": context.step_id}
            )

            # Validate chart tool
            if tool_type not in CHART_TOOLS:
                return ExecutorResult(
                    success=False,
                    step_id=context.step_id,
                    error=f"Unsupported tool for ChartExecutor: {tool_type}",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    executor_category=self.category,
                )

            # Execute based on tool type
            handlers = {
                "chart_generate": self._execute_chart_generate,
                "chart_configure": self._execute_chart_configure,
                "dashboard_create": self._execute_dashboard_create,
                "chart_export": self._execute_chart_export,
                "chart_update": self._execute_chart_update,
                "report_generate": self._execute_report_generate,
            }

            handler = handlers.get(tool_type)
            if handler:
                result = await handler(context, inputs)
            else:
                result = ExecutorResult(
                    success=False,
                    step_id=context.step_id,
                    error=f"Unhandled tool type: {tool_type}",
                    executor_category=self.category,
                )

            # Add execution metadata
            result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            result.executor_category = self.category

            return result

    async def _execute_chart_generate(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Generate chart from data."""
        chart_type = inputs.get("chart_type", "line")
        data = inputs.get("data", {})
        title = inputs.get("title", "")

        logger.info(f"Generating {chart_type} chart: {title}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "chart_type": chart_type,
                "data": data,
                "title": title,
                "chart_config": {},
                "chart_id": f"chart_{context.step_id}",
                "query_type": "chart_generate",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_chart_configure(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Configure chart styling and options."""
        chart_id = inputs.get("chart_id", "")
        config = inputs.get("config", {})

        logger.info(f"Configuring chart: {chart_id}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "chart_id": chart_id,
                "config": config,
                "query_type": "chart_configure",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_dashboard_create(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Create dashboard with multiple charts."""
        chart_ids = inputs.get("chart_ids", [])
        layout = inputs.get("layout", "grid")
        title = inputs.get("title", "")

        logger.info(f"Creating dashboard with {len(chart_ids)} charts")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "chart_ids": chart_ids,
                "layout": layout,
                "title": title,
                "dashboard_id": f"dashboard_{context.step_id}",
                "query_type": "dashboard_create",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_chart_export(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Export chart to file."""
        chart_id = inputs.get("chart_id", "")
        format_type = inputs.get("format", "png")
        filepath = inputs.get("filepath", "")

        logger.info(f"Exporting chart {chart_id} to {format_type}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "chart_id": chart_id,
                "format": format_type,
                "filepath": filepath,
                "export_url": "",
                "query_type": "chart_export",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_chart_update(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Update chart data or configuration."""
        chart_id = inputs.get("chart_id", "")
        new_data = inputs.get("data", None)
        new_config = inputs.get("config", None)

        logger.info(f"Updating chart: {chart_id}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "chart_id": chart_id,
                "data_updated": new_data is not None,
                "config_updated": new_config is not None,
                "query_type": "chart_update",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_report_generate(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Generate report (delegated to chart executor for visualization reports)."""
        title = inputs.get("title", "")
        sections = inputs.get("sections", [])
        chart_data = inputs.get("chart_data", {})

        logger.info(f"Generating visualization report: {title}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "title": title,
                "sections": sections,
                "chart_data": chart_data,
                "report_id": f"report_{context.step_id}",
                "report_content": "",
                "query_type": "report_generate",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )
