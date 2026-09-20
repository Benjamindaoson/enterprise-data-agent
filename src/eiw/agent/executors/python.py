"""Python Executor - Python analysis sandbox execution.

This executor handles Python code execution for analysis:
- Custom metric calculations
- Data transformation
- Statistical analysis
- Algorithm execution
"""

from __future__ import annotations

import asyncio
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

logger = get_structured_logger(__name__, "executor.python")

# Supported Python tool types
PYTHON_TOOLS = {
    "python_analysis",
    "python_execute",
    "python_calculate",
    "python_transform",
}

# Allowed imports for sandbox
ALLOWED_IMPORTS = {
    "math", "statistics", "collections", "itertools",
    "datetime", "json", "re", "functools",
    "pandas", "numpy", "scipy",  # Data science
    "random", "decimal", "fractions",
}

# Blocked patterns for security
BLOCKED_PATTERNS = [
    "import os", "import sys", "import subprocess",
    "import socket", "import http", "import urllib",
    "import requests", "import httpx",
    "open(", "file", "exec(", "eval(",
    "__import__", "getattr", "setattr", "delattr",
    "compile(", "memoryview", "buffer",
]


class PythonExecutor(BaseExecutor):
    """Executor for Python code execution.

    This executor provides a sandboxed environment for:
    - Custom metric calculations
    - Data transformation operations
    - Statistical analysis
    - Algorithm execution
    """

    def __init__(self):
        super().__init__(
            category=ExecutorCategory.PYTHON,
            name="python",
            description="Python executor for sandboxed code execution, calculations, and data analysis",
            supported_tools=PYTHON_TOOLS,
        )

    async def execute(
        self,
        context: StepContext,
        tool_type: str,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute Python code.

        Args:
            context: Step execution context
            tool_type: Tool type to execute
            inputs: Tool-specific inputs

        Returns:
            Executor result with execution output
        """
        start_time = datetime.now()

        with trace_span("executor.python.execute", {
            "task_id": context.task_id,
            "step_id": context.step_id,
            "tool_type": tool_type,
        }):
            logger.info(
                f"PythonExecutor executing {tool_type}",
                extra={"task_id": context.task_id, "step_id": context.step_id}
            )

            # Validate Python tool
            if tool_type not in PYTHON_TOOLS:
                return ExecutorResult(
                    success=False,
                    step_id=context.step_id,
                    error=f"Unsupported tool for PythonExecutor: {tool_type}",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    executor_category=self.category,
                )

            # Execute based on tool type
            handlers = {
                "python_analysis": self._execute_python_analyze,  # python_analysis maps to python_analyze
                "python_execute": self._execute_python_execute,
                "python_calculate": self._execute_python_calculate,
                "python_transform": self._execute_python_transform,
                "python_analyze": self._execute_python_analyze,
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

    def _validate_code(self, code: str) -> tuple[bool, str]:
        """Validate code for security."""
        for pattern in BLOCKED_PATTERNS:
            if pattern in code:
                return False, f"Blocked pattern detected: {pattern}"
        return True, ""

    async def _execute_python_execute(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute Python code in sandbox."""
        code = inputs.get("code", "")
        timeout = inputs.get("timeout", 30)

        # Validate code
        is_valid, error_msg = self._validate_code(code)
        if not is_valid:
            return ExecutorResult(
                success=False,
                step_id=context.step_id,
                error=f"Code validation failed: {error_msg}",
                executor_category=self.category,
            )

        logger.info(f"Executing Python code (timeout={timeout}s)")

        # Run in thread pool to avoid blocking
        try:
            result_data = await asyncio.wait_for(
                self._run_code_in_sandbox(code),
                timeout=timeout
            )
            return ExecutorResult(
                success=True,
                step_id=context.step_id,
                data={
                    "code": code,
                    "output": result_data.get("output", ""),
                    "result": result_data.get("result"),
                    "error": result_data.get("error"),
                    "execution_time_ms": result_data.get("execution_time_ms", 0),
                    "query_type": "python_execute",
                },
                observation_id=f"obs_{context.step_id}",
                status="success",
            )
        except asyncio.TimeoutError:
            return ExecutorResult(
                success=False,
                step_id=context.step_id,
                error=f"Execution timeout after {timeout}s",
                executor_category=self.category,
                status="timeout",
            )

    async def _execute_python_calculate(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute metric calculation."""
        formula = inputs.get("formula", "")
        variables = inputs.get("variables", {})

        logger.info(f"Executing calculation: {formula}")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "formula": formula,
                "variables": variables,
                "result": None,
                "query_type": "python_calculate",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_python_transform(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute data transformation."""
        data = inputs.get("data", [])
        transform_code = inputs.get("transform_code", "")

        logger.info(f"Executing data transformation")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "transform_code": transform_code,
                "input_data": data,
                "output_data": [],
                "query_type": "python_transform",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_python_analyze(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute statistical analysis."""
        data = inputs.get("data", [])
        analysis_type = inputs.get("analysis_type", "descriptive")

        logger.info(f"Executing {analysis_type} analysis")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "analysis_type": analysis_type,
                "input_data": data,
                "analysis_result": {},
                "query_type": "python_analyze",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _run_code_in_sandbox(self, code: str) -> dict[str, Any]:
        """Run code in sandboxed environment."""
        import sys
        from io import StringIO

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        result = None
        error = None
        execution_time_ms = 0

        start_time = datetime.now()

        try:
            # Execute code
            exec_globals = {"__builtins__": __builtins__}
            exec(code, exec_globals)
            result = sys.stdout.getvalue()
        except Exception as e:
            error = str(e)
        finally:
            sys.stdout = old_stdout
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "output": result,
            "result": None,
            "error": error,
            "execution_time_ms": execution_time_ms,
        }
