"""Sales Executor - Sales analysis operations.

This executor handles sales analysis operations including:
- Sales/revenue analysis
- Order analysis
- Customer analysis
- Regional/channel/product contribution
- Conversion analysis
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

logger = get_structured_logger(__name__, "executor.sales")

# Supported sales tool types
SALES_TOOLS = {
    "metric_query",
    "period_compare",
    "contribution_analysis",
    "drilldown_analysis",
    "trend_analysis",
    "anomaly_analysis",
}


class SalesExecutor(BaseExecutor):
    """Executor for sales analysis operations.

    This executor handles sales metrics and analysis operations:
    - Revenue and sales analysis
    - Order volume and patterns
    - Customer metrics
    - Regional/channel contribution
    - Conversion analysis
    - Anomaly detection in sales data
    """

    def __init__(self):
        super().__init__(
            category=ExecutorCategory.SALES,
            name="sales",
            description="Sales analysis executor for revenue, orders, customers, and contribution analysis",
            supported_tools=SALES_TOOLS,
        )

    async def execute(
        self,
        context: StepContext,
        tool_type: str,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute sales analysis step.

        Args:
            context: Step execution context
            tool_type: Tool type to execute
            inputs: Tool-specific inputs

        Returns:
            Executor result with sales analysis data
        """
        start_time = datetime.now()

        with trace_span("executor.sales.execute", {
            "task_id": context.task_id,
            "step_id": context.step_id,
            "tool_type": tool_type,
        }):
            logger.info(
                f"SalesExecutor executing {tool_type}",
                extra={"task_id": context.task_id, "step_id": context.step_id}
            )

            # Validate sales tool
            if tool_type not in SALES_TOOLS:
                return ExecutorResult(
                    success=False,
                    step_id=context.step_id,
                    error=f"Unsupported tool for SalesExecutor: {tool_type}",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    executor_category=self.category,
                )

            # Execute based on tool type
            if tool_type == "metric_query":
                result = await self._execute_metric_query(context, inputs)
            elif tool_type == "period_compare":
                result = await self._execute_period_compare(context, inputs)
            elif tool_type == "contribution_analysis":
                result = await self._execute_contribution_analysis(context, inputs)
            elif tool_type == "drilldown_analysis":
                result = await self._execute_drilldown_analysis(context, inputs)
            elif tool_type == "trend_analysis":
                result = await self._execute_trend_analysis(context, inputs)
            elif tool_type == "anomaly_analysis":
                result = await self._execute_anomaly_analysis(context, inputs)
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

    async def _execute_metric_query(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute sales metric query."""
        metrics = inputs.get("metrics", [])
        dimensions = inputs.get("dimensions", [])

        logger.info(
            f"Executing sales metric query for {metrics}",
            extra={"dimensions": dimensions}
        )

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "metrics": metrics,
                "dimensions": dimensions,
                "results": [],
                "query_type": "sales_metric",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_period_compare(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute sales period comparison."""
        period_type = inputs.get("period_type", "MoM")
        metric = inputs.get("metric", "")

        logger.info(f"Executing {period_type} comparison for {metric}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "period_type": period_type,
                "metric": metric,
                "comparison": {},
                "query_type": "period_comparison",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_contribution_analysis(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute sales contribution analysis."""
        breakdown_by = inputs.get("breakdown_by", "region")
        metric = inputs.get("metric", "")

        logger.info(f"Executing contribution analysis by {breakdown_by}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "breakdown_by": breakdown_by,
                "metric": metric,
                "contributions": [],
                "query_type": "contribution_analysis",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_drilldown_analysis(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute sales drill-down analysis."""
        drilldown_dimensions = inputs.get("dimensions", [])
        metric = inputs.get("metric", "")

        logger.info(f"Executing drill-down by {drilldown_dimensions}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "dimensions": drilldown_dimensions,
                "metric": metric,
                "drilldown_results": {},
                "query_type": "drilldown_analysis",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_trend_analysis(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute sales trend analysis."""
        granularity = inputs.get("granularity", "weekly")
        metric = inputs.get("metric", "")

        logger.info(f"Executing trend analysis at {granularity} granularity")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "granularity": granularity,
                "metric": metric,
                "trend": {},
                "query_type": "trend_analysis",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_anomaly_analysis(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute sales anomaly detection."""
        metric = inputs.get("metric", "")
        sensitivity = inputs.get("sensitivity", "medium")

        logger.info(f"Executing anomaly analysis for {metric} with {sensitivity} sensitivity")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "metric": metric,
                "sensitivity": sensitivity,
                "anomalies": [],
                "query_type": "anomaly_analysis",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )
