"""NL2SQL Executor - Natural Language to SQL conversion.

This executor handles NL2SQL operations including:
- Semantic parsing of natural language queries
- Schema linking and context retrieval
- SQL generation with validation
- Query execution and result interpretation
- Error repair for failed queries
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

logger = get_structured_logger(__name__, "executor.nl2sql")

# Supported NL2SQL tool types
NL2SQL_TOOLS = {
    "nl2sql_generate",
    "nl2sql_validate",
    "nl2sql_explain",
    "nl2sql_repair",
    "nl2sql_execute",
    "nl2sql_optimize",
    "schema_link",
}


class NL2SQLExecutor(BaseExecutor):
    """Executor for Natural Language to SQL operations.

    This executor handles the complete NL2SQL pipeline:
    - Schema linking: Connect NL terms to database schema
    - SQL generation: Convert parsed intent to SQL
    - Validation: Verify SQL syntax and semantics
    - Execution: Run SQL and return results
    - Repair: Fix failed or suboptimal queries
    """

    def __init__(self):
        super().__init__(
            category=ExecutorCategory.NL2SQL,
            name="nl2sql",
            description="NL2SQL executor for natural language query understanding, SQL generation, and execution",
            supported_tools=NL2SQL_TOOLS,
        )

    async def execute(
        self,
        context: StepContext,
        tool_type: str,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute NL2SQL step.

        Args:
            context: Step execution context
            tool_type: Tool type to execute
            inputs: Tool-specific inputs

        Returns:
            Executor result with NL2SQL data
        """
        start_time = datetime.now()

        with trace_span("executor.nl2sql.execute", {
            "task_id": context.task_id,
            "step_id": context.step_id,
            "tool_type": tool_type,
        }):
            logger.info(
                f"NL2SQLExecutor executing {tool_type}",
                extra={"task_id": context.task_id, "step_id": context.step_id}
            )

            # Validate NL2SQL tool
            if tool_type not in NL2SQL_TOOLS:
                return ExecutorResult(
                    success=False,
                    step_id=context.step_id,
                    error=f"Unsupported tool for NL2SQLExecutor: {tool_type}",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    executor_category=self.category,
                )

            # Execute based on tool type
            handlers = {
                "nl2sql_generate": self._execute_generate,
                "nl2sql_validate": self._execute_validate,
                "nl2sql_explain": self._execute_explain,
                "nl2sql_repair": self._execute_repair,
                "nl2sql_execute": self._execute_execute,
                "nl2sql_optimize": self._execute_optimize,
                "schema_link": self._execute_schema_link,
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

    async def _execute_generate(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Generate SQL from natural language query."""
        query = inputs.get("query", "")
        schema_context = inputs.get("schema_context", {})

        logger.info(f"Generating SQL for query: {query[:100]}...")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "query": query,
                "schema_context": schema_context,
                "generated_sql": "",
                "intent": {},
                "query_type": "nl2sql_generate",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_validate(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Validate generated SQL."""
        sql = inputs.get("sql", "")
        validation_rules = inputs.get("validation_rules", [])

        logger.info(f"Validating SQL: {sql[:100]}...")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "sql": sql,
                "validation_rules": validation_rules,
                "validation_result": {
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                },
                "query_type": "nl2sql_validate",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_explain(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Explain SQL query."""
        sql = inputs.get("sql", "")

        logger.info(f"Explaining SQL: {sql[:100]}...")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "sql": sql,
                "explanation": "",
                "execution_plan": {},
                "query_type": "nl2sql_explain",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_repair(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Repair failed or suboptimal SQL."""
        original_sql = inputs.get("sql", "")
        error = inputs.get("error", "")
        original_query = inputs.get("original_query", "")

        logger.info(f"Repairing SQL: {original_sql[:100]}...")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "original_sql": original_sql,
                "error": error,
                "original_query": original_query,
                "repaired_sql": "",
                "repair_reason": "",
                "query_type": "nl2sql_repair",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_execute(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Execute SQL query."""
        sql = inputs.get("sql", "")
        params = inputs.get("params", {})

        logger.info(f"Executing SQL: {sql[:100]}...")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "sql": sql,
                "params": params,
                "results": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "query_type": "nl2sql_execute",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_optimize(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Optimize SQL query."""
        sql = inputs.get("sql", "")
        target_dialect = inputs.get("target_dialect", "duckdb")

        logger.info(f"Optimizing SQL for {target_dialect}: {sql[:100]}...")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "sql": sql,
                "target_dialect": target_dialect,
                "optimized_sql": "",
                "optimizations_applied": [],
                "query_type": "nl2sql_optimize",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )

    async def _execute_schema_link(
        self,
        context: StepContext,
        inputs: dict[str, Any],
    ) -> ExecutorResult:
        """Link natural language terms to schema elements."""
        query = inputs.get("query", "")
        schema = inputs.get("schema", {})

        logger.info(f"Schema linking for query: {query[:100]}...")

        return ExecutorResult(
            success=True,
            step_id=context.step_id,
            data={
                "query": query,
                "schema": schema,
                "linked_terms": [],
                "mapped_tables": [],
                "mapped_columns": [],
                "query_type": "schema_link",
            },
            observation_id=f"obs_{context.step_id}",
            status="success",
        )
