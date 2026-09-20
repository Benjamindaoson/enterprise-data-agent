"""SQL Generator - Generates SQL from logical plans and context.

This module generates SQL using:
- Resolved business intent
- Semantic context
- Relevant schema
- Logical query plan
- Approved examples
- Policy constraints
"""

from __future__ import annotations

import hashlib
from typing import Any

from eiw.nl2sql.contracts import (
    GeneratedSQL,
    LogicalQueryPlan,
    SchemaContext,
    SQLGeneratorProvider,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "sql_generator")


class MockSQLGenerator(SQLGeneratorProvider):
    """Mock SQL generator for testing and offline use.

    This generator creates SQL from structured plans without calling an LLM.
    Used for testing and deterministic scenarios.
    """

    def __init__(self) -> None:
        """Initialize mock generator."""
        super().__init__(provider_name="mock", model_name="mock-v1")

    def generate(
        self,
        question: str,
        schema_context: SchemaContext,
        logical_plan: LogicalQueryPlan,
        examples: list[GeneratedSQL],
        policy_constraints: dict[str, Any],
    ) -> GeneratedSQL:
        """Generate SQL from structured plan.

        Args:
            question: Original question
            schema_context: Schema context
            logical_plan: Logical query plan
            examples: Approved SQL examples
            policy_constraints: Policy constraints

        Returns:
            Generated SQL
        """
        with trace_span("nl2sql.generate", {
            "provider": self.provider_name,
            "model": self.model_name,
            "purpose": logical_plan.purpose,
        }):
            # Build SQL from plan
            sql_parts: list[str] = []

            # SELECT clause
            select_cols = self._build_select(logical_plan, schema_context)
            sql_parts.append(f"SELECT {select_cols}")

            # FROM clause
            if logical_plan.source_candidates:
                sql_parts.append(f"FROM {logical_plan.source_candidates[0]}")

            # JOINs
            joins_sql = self._build_joins(logical_plan, schema_context)
            if joins_sql:
                sql_parts.append(joins_sql)

            # WHERE clause
            where_sql = self._build_where(logical_plan)
            if where_sql:
                sql_parts.append(f"WHERE {where_sql}")

            # GROUP BY clause
            if logical_plan.grouping:
                sql_parts.append(f"GROUP BY {', '.join(logical_plan.grouping)}")

            # ORDER BY clause
            order_sql = self._build_order_by(logical_plan)
            if order_sql:
                sql_parts.append(f"ORDER BY {order_sql}")

            # LIMIT clause
            if logical_plan.limit:
                sql_parts.append(f"LIMIT {logical_plan.limit}")

            sql = "\n".join(sql_parts)

            # Extract metadata
            tables_used = logical_plan.source_candidates.copy()
            columns_used = [c for c in logical_plan.grouping] if logical_plan.grouping else []

            # Calculate hash
            sql_hash = hashlib.sha256(sql.encode()).hexdigest()[:16]

            logger.info(
                f"SQL generated: {len(sql)} chars",
                extra={
                    "sql_hash": sql_hash,
                    "tables_used": tables_used,
                    "columns_used": columns_used,
                }
            )

            return GeneratedSQL(
                sql=sql,
                tables_used=tables_used,
                columns_used=columns_used,
                metrics_calculated=logical_plan.metrics,
                confidence=0.85,
                explanation=f"Generated SQL from plan: {logical_plan.purpose}",
                provider=self.provider_name,
                model=self.model_name,
                prompt_version="1.0",
                sql_hash=sql_hash,
            )

    def _build_select(
        self,
        plan: LogicalQueryPlan,
        schema: SchemaContext,
    ) -> str:
        """Build SELECT clause.

        Args:
            plan: Logical query plan
            schema: Schema context

        Returns:
            SELECT clause SQL
        """
        cols: list[str] = []

        # Add grouping columns
        for dim in plan.dimensions:
            if dim in schema.tables:
                table = schema.tables[dim]
                if table.columns:
                    cols.append(table.columns[0].name)
                else:
                    cols.append(dim)
            else:
                cols.append(dim)

        # Add metric aggregations
        for metric in plan.metrics:
            agg = plan.aggregation or "SUM"
            cols.append(f"{agg}({metric}) AS {metric}")

        if not cols:
            return "*"

        return ", ".join(cols)

    def _build_joins(
        self,
        plan: LogicalQueryPlan,
        schema: SchemaContext,
    ) -> str:
        """Build JOIN clauses.

        Args:
            plan: Logical query plan
            schema: Schema context

        Returns:
            JOIN clauses SQL
        """
        if not plan.joins:
            return ""

        join_parts: list[str] = []

        for join_spec in plan.joins:
            join_type = join_spec.get("join_type", "INNER")
            to_table = join_spec.get("to_table", "")
            to_col = join_spec.get("to_column", "id")
            from_col = join_spec.get("from_column", "id")

            join_parts.append(
                f"{join_type} JOIN {to_table} ON {to_table}.{to_col} = "
                f"{plan.source_candidates[0] if plan.source_candidates else 't'}.{from_col}"
            )

        return "\n".join(join_parts)

    def _build_where(self, plan: LogicalQueryPlan) -> str:
        """Build WHERE clause.

        Args:
            plan: Logical query plan

        Returns:
            WHERE clause SQL
        """
        conditions: list[str] = []

        # Add filter conditions
        for key, value in plan.filters.items():
            if key == "time_period":
                # Convert time period to actual condition
                pass  # Would need actual date handling
            elif isinstance(value, (int, float)):
                conditions.append(f"{key} = {value}")
            elif isinstance(value, str):
                conditions.append(f"{key} = '{value}'")
            elif isinstance(value, list):
                conditions.append(f"{key} IN ({', '.join(str(v) for v in value)})")

        return " AND ".join(conditions)

    def _build_order_by(self, plan: LogicalQueryPlan) -> str:
        """Build ORDER BY clause.

        Args:
            plan: Logical query plan

        Returns:
            ORDER BY clause SQL
        """
        if not plan.ordering:
            return ""

        parts: list[str] = []
        for order in plan.ordering:
            col = order.get("column", "value")
            direction = order.get("direction", "ASC")
            parts.append(f"{col} {direction}")

        return ", ".join(parts)


class LLMSQLGenerator(SQLGeneratorProvider):
    """LLM-based SQL generator.

    This generator uses an LLM to generate SQL from natural language.
    Requires a real LLM provider.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        base_url: str | None = None,
    ) -> None:
        """Initialize LLM generator.

        Args:
            api_key: API key for LLM provider
            model: Model name
            base_url: Base URL for API (optional)
        """
        super().__init__(provider_name="anthropic", model_name=model)
        self._api_key = api_key
        self._base_url = base_url

    def generate(
        self,
        question: str,
        schema_context: SchemaContext,
        logical_plan: LogicalQueryPlan,
        examples: list[GeneratedSQL],
        policy_constraints: dict[str, Any],
    ) -> GeneratedSQL:
        """Generate SQL using LLM.

        Args:
            question: Natural language question
            schema_context: Available schema
            logical_plan: Query plan
            examples: Approved SQL examples
            policy_constraints: Policy constraints

        Returns:
            Generated SQL

        Raises:
            NotImplementedError: Must be properly configured with API key
        """
        with trace_span("nl2sql.generate", {
            "provider": self.provider_name,
            "model": self.model_name,
        }):
            if not self._api_key:
                raise NotImplementedError(
                    "LLM SQL generator requires API key. "
                    "Use MockSQLGenerator for offline testing."
                )

            # Build prompt
            prompt = self._build_prompt(
                question,
                schema_context,
                logical_plan,
                examples,
                policy_constraints,
            )

            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            sql = self._extract_sql(response)

            # Calculate hash
            sql_hash = hashlib.sha256(sql.encode()).hexdigest()[:16]

            return GeneratedSQL(
                sql=sql,
                confidence=0.8,  # LLM confidence
                explanation="Generated by LLM",
                provider=self.provider_name,
                model=self.model_name,
                prompt_version="1.0",
                sql_hash=sql_hash,
            )

    def _build_prompt(
        self,
        question: str,
        schema: SchemaContext,
        plan: LogicalQueryPlan,
        examples: list[GeneratedSQL],
        constraints: dict[str, Any],
    ) -> str:
        """Build LLM prompt.

        Args:
            question: User question
            schema: Schema context
            plan: Query plan
            examples: SQL examples
            constraints: Policy constraints

        Returns:
            Formatted prompt
        """
        prompt_parts = [
            "You are a SQL expert. Generate a SQL query to answer the following question.",
            "",
            f"Question: {question}",
            "",
            "Schema:",
        ]

        # Add schema information
        for table_name, table in schema.tables.items():
            prompt_parts.append(f"  Table: {table_name}")
            if table.description:
                prompt_parts.append(f"    Description: {table.description}")
            for col in table.columns:
                prompt_parts.append(f"    - {col.name} ({col.data_type}): {col.description}")

        # Add query plan context
        if plan.metrics:
            prompt_parts.append(f"\nMetrics: {', '.join(plan.metrics)}")
        if plan.dimensions:
            prompt_parts.append(f"Dimensions: {', '.join(plan.dimensions)}")
        if plan.aggregation:
            prompt_parts.append(f"Aggregation: {plan.aggregation}")

        # Add examples
        if examples:
            prompt_parts.append("\nExamples:")
            for ex in examples[:3]:  # Limit examples
                prompt_parts.append(f"  - {ex.sql}")

        # Add policy constraints
        if constraints:
            prompt_parts.append("\nPolicy Constraints:")
            for key, value in constraints.items():
                prompt_parts.append(f"  - {key}: {value}")

        prompt_parts.append("\nGenerate the SQL query:")

        return "\n".join(prompt_parts)

    def _call_llm(self, prompt: str) -> str:
        """Call LLM API.

        Args:
            prompt: Prompt text

        Returns:
            LLM response

        Raises:
            NotImplementedError: Must be implemented with actual API call
        """
        # This is a placeholder - would need actual API implementation
        raise NotImplementedError(
            "LLM API call not implemented. "
            "Configure with actual API credentials."
        )

    def _extract_sql(self, response: str) -> str:
        """Extract SQL from LLM response.

        Args:
            response: LLM response text

        Returns:
            Extracted SQL
        """
        # Try to extract SQL from markdown code block
        if "```sql" in response:
            parts = response.split("```sql")
            if len(parts) > 1:
                sql_part = parts[1].split("```")[0]
                return sql_part.strip()

        if "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                return parts[1].strip()

        # Return as-is if no code block
        return response.strip()


def create_sql_generator(
    provider: str = "mock",
    **kwargs: Any,
) -> SQLGeneratorProvider:
    """Create a SQL generator provider.

    Args:
        provider: Provider name ("mock" or "llm")
        **kwargs: Provider-specific arguments

    Returns:
        SQL generator provider
    """
    if provider == "mock":
        return MockSQLGenerator()
    elif provider == "llm":
        return LLMSQLGenerator(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
