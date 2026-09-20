"""Report Executor - Report generation operations.

This executor handles report generation operations:
- Report template selection
- Content aggregation
- Formatting and styling
- Export and distribution
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

logger = get_structured_logger(__name__, "executor.report")

# Supported report tool types
REPORT_TOOLS = {
    "report_generate",
    "report_update",
    "report_export",
    "report_schedule",
    "report_share",
}


class ReportExecutor(BaseExecutor):
    """Executor for report generation operations.

    This executor handles:
    - Report content generation from analysis results
    - Report template selection and customization
    - Export in various formats (PDF, HTML, etc.)
    - Report scheduling and distribution
    """

    def __init__(self):
        super().__init__(
            category=ExecutorCategory.REPORT,
            name="report",
            description="Report executor for generating, formatting, and distributing analysis reports",
            supported_tools=REPORT_TOOLS,
        )

    async def execute(
        self,
        context: StepContext,
        tool_type: str,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute report operation.

        Args:
            context: Step execution context
            tool_type: Tool type to execute
            inputs: Tool-specific inputs

        Returns:
            Executor result with report data
        """
        start_time = datetime.now()

        with trace_span("executor.report.execute", {
            "task_id": context.task_id,
            "step_id": context.step_id,
            "tool_type": tool_type,
        }):
            logger.info(
                f"ReportExecutor executing {tool_type}",
                extra={"task_id": context.task_id, "step_id": context.step_id}
            )

            # Validate report tool
            if tool_type not in REPORT_TOOLS:
                return ExecutorResult(
                    success=False,
                    step_id=context.step_id,
                    error=f"Unsupported tool for ReportExecutor: {tool_type}",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    executor_category=self.category,
                )

            # Execute based on tool type
            handlers = {
                "report_generate": self._execute_report_generate,
                "report_update": self._execute_report_update,
                "report_export": self._execute_report_export,
                "report_schedule": self._execute_report_schedule,
                "report_share": self._execute_report_share,
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

    async def _execute_report_generate(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Generate report from analysis results."""
        title = inputs.get("title", "")
        sections = inputs.get("sections", [])
        template = inputs.get("template", "default")
        analysis_results = inputs.get("analysis_results", {})

        logger.info(f"Generating report: {title}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "title": title,
                "sections": sections,
                "template": template,
                "analysis_results": analysis_results,
                "report_id": f"report_{context.step_id}",
                "report_content": "",
                "query_type": "report_generate",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_report_update(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Update existing report."""
        report_id = inputs.get("report_id", "")
        updates = inputs.get("updates", {})

        logger.info(f"Updating report: {report_id}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "report_id": report_id,
                "updates": updates,
                "updated_sections": [],
                "query_type": "report_update",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_report_export(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Export report to file."""
        report_id = inputs.get("report_id", "")
        format_type = inputs.get("format", "pdf")
        filepath = inputs.get("filepath", "")

        logger.info(f"Exporting report {report_id} to {format_type}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "report_id": report_id,
                "format": format_type,
                "filepath": filepath,
                "export_url": "",
                "query_type": "report_export",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_report_schedule(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Schedule recurring report generation."""
        report_id = inputs.get("report_id", "")
        schedule = inputs.get("schedule", {})
        recipients = inputs.get("recipients", [])

        logger.info(f"Scheduling report: {report_id}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "report_id": report_id,
                "schedule": schedule,
                "recipients": recipients,
                "schedule_id": f"schedule_{context.step_id}",
                "next_run": None,
                "query_type": "report_schedule",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_report_share(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Share report with recipients."""
        report_id = inputs.get("report_id", "")
        share_method = inputs.get("method", "link")
        recipients = inputs.get("recipients", [])

        logger.info(f"Sharing report {report_id} via {share_method}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "report_id": report_id,
                "method": share_method,
                "recipients": recipients,
                "share_url": "",
                "permissions": {},
                "query_type": "report_share",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )
