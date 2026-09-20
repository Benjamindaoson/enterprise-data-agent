"""Default Executor - Fallback executor for unmatched tools.

This executor serves as the fallback when no specialized executor
is available for a given tool type.
"""

from __future__ import annotations

from datetime import datetime

from eiw.agent.executor import (
    BaseExecutor,
    ExecutorCategory,
    ExecutorResult,
    StepContext,
)
from eiw.observability.logging import get_structured_logger
from eiw.observability.otel import trace_span

logger = get_structured_logger(__name__, "executor")


class DefaultExecutor(BaseExecutor):
    """Default executor for unmatched tool types.

    This executor handles any tool type that doesn't have a specialized executor.
    It provides basic execution with logging and tracing.
    """

    def __init__(self):
        super().__init__(
            category=ExecutorCategory.DEFAULT,
            name="default",
            description="Default executor for unmatched tools",
            supported_tools=set(),  # Handles everything as fallback
        )

    async def execute(
        self,
        context: StepContext,
        tool_type: str,  # noqa: ARG002
        inputs: dict,
    ) -> ExecutorResult:
        """Execute using default behavior.

        Args:
            context: Step context
            tool_type: Tool type (unused in default executor)
            inputs: Tool inputs

        Returns:
            Executor result with warning
        """
        start_time = datetime.now()

        with trace_span("executor.default.execute", {
            "task_id": context.task_id,
            "step_id": context.step_id,
            "category": self.category.value,
        }):
            logger.warning(
                f"Using default executor for step {context.step_id}",
                extra={
                    "task_id": context.task_id,
                    "step_id": context.step_id,
                    "inputs": inputs,
                }
            )

            # For default executor, we just acknowledge the step was processed
            # In production, this would delegate to the tool registry
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return ExecutorResult(
                success=True,
                step_id=context.step_id,
                data={
                    "status": "processed",
                    "executor": "default",
                    "message": "Step processed by default executor",
                },
                duration_ms=duration_ms,
                status="success",
                warnings=["Using fallback default executor - consider adding specialized executor"],
                executor_category=self.category,
            )
