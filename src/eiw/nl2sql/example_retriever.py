"""SQL Example Retriever - Retrieves approved SQL examples for context.

This module retrieves SQL examples from the knowledge base:
- Examples are permission-aware
- Examples have domain/version/source
- Examples are only used as generation context
- Outdated schema examples are detected
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eiw.nl2sql.contracts import GeneratedSQL
from eiw.knowledge.base import (
    KnowledgeBase,
    KnowledgeRetrievalQuery,
    KnowledgeRetrievalResult,
    KnowledgeSourceType,
    PermissionLevel,
    get_knowledge_base,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "example_retriever")


@dataclass
class SQLExample:
    """A SQL example from the knowledge base."""

    title: str
    sql: str
    description: str
    domain: str
    version: str
    related_metrics: list[str] = field(default_factory=list)
    related_tables: list[str] = field(default_factory=list)
    permission_level: PermissionLevel = PermissionLevel.INTERNAL
    is_current_schema: bool = True


@dataclass
class ExampleRetrievalResult:
    """Result of SQL example retrieval."""

    examples: list[SQLExample]
    total_found: int
    filtered_by_permission: bool = False
    filtered_by_schema: bool = False


class ExampleRetriever:
    """Retrieves approved SQL examples for SQL generation.

    This retriever:
    1. Queries knowledge base for SQL examples
    2. Filters by permission level
    3. Validates schema compatibility
    4. Returns only current, approved examples
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase | None = None,
        current_schema_version: str = "1.0.0",
    ) -> None:
        """Initialize example retriever.

        Args:
            knowledge_base: Knowledge base instance
            current_schema_version: Current schema version for validation
        """
        self._kb = knowledge_base or get_knowledge_base()
        self._current_schema_version = current_schema_version

    def retrieve(
        self,
        domain: str,
        related_metrics: list[str] | None = None,
        related_tables: list[str] | None = None,
        max_examples: int = 5,
        user_permission_level: PermissionLevel = PermissionLevel.INTERNAL,
    ) -> ExampleRetrievalResult:
        """Retrieve SQL examples for the given context.

        Args:
            domain: Business domain
            related_metrics: Related metric IDs
            related_tables: Related table names
            max_examples: Maximum examples to return
            user_permission_level: User's permission level

        Returns:
            Retrieval result with filtered examples
        """
        with trace_span("nl2sql.example_retrieve", {
            "domain": domain,
            "related_metrics": related_metrics,
            "max_examples": max_examples,
        }):
            # Query knowledge base
            query = KnowledgeRetrievalQuery(
                query_text=f"SQL example {domain}",
                query_type=KnowledgeSourceType.SQL_EXAMPLE,
                domain_ids=[domain] if domain else [],
                related_metric_ids=related_metrics or [],
                max_permission_level=user_permission_level,
                max_results=max_examples * 2,  # Get more to filter
            )

            kb_result = self._kb.retrieve(query)

            examples: list[SQLExample] = []
            filtered_by_permission = False
            filtered_by_schema = False

            for item in kb_result.items:
                # Create example from knowledge item
                example = self._item_to_example(item)

                # Check permission
                if not self._check_permission(example.permission_level, user_permission_level):
                    filtered_by_permission = True
                    continue

                # Check schema version compatibility
                if example.version != self._current_schema_version:
                    # Check if it's significantly outdated
                    if self._is_schema_compatible(example.version, self._current_schema_version):
                        example.is_current_schema = True
                    else:
                        filtered_by_schema = True
                        continue

                # Filter by table if specified
                if related_tables:
                    if not any(table in example.related_tables for table in related_tables):
                        # Still include if related metrics match
                        if not any(m in example.related_metrics for m in (related_metrics or [])):
                            continue

                examples.append(example)

                if len(examples) >= max_examples:
                    break

            logger.info(
                f"Retrieved {len(examples)} SQL examples",
                extra={
                    "domain": domain,
                    "examples_found": kb_result.total_found,
                    "examples_returned": len(examples),
                    "filtered_by_permission": filtered_by_permission,
                    "filtered_by_schema": filtered_by_schema,
                }
            )

            return ExampleRetrievalResult(
                examples=examples,
                total_found=len(examples),
                filtered_by_permission=filtered_by_permission,
                filtered_by_schema=filtered_by_schema,
            )

    def _item_to_example(self, item: Any) -> SQLExample:
        """Convert knowledge item to SQL example.

        Args:
            item: Knowledge item

        Returns:
            SQL example
        """
        # Extract SQL from content
        sql = self._extract_sql_from_content(item.content)

        return SQLExample(
            title=item.title,
            sql=sql,
            description=item.content.split("```")[0].strip() if "```" in item.content else item.content,
            domain=item.domain_id or "",
            version=item.semantic_version or "1.0.0",
            related_metrics=item.related_metric_ids,
            related_tables=item.related_table_names,
            permission_level=item.permission_level,
            is_current_schema=True,
        )

    def _extract_sql_from_content(self, content: str) -> str:
        """Extract SQL from content that may have markdown code blocks.

        Args:
            content: Content text

        Returns:
            Extracted SQL
        """
        if "```sql" in content:
            parts = content.split("```sql")
            if len(parts) > 1:
                sql_part = parts[1].split("```")[0]
                return sql_part.strip()

        if "```" in content:
            parts = content.split("```")
            if len(parts) > 1:
                return parts[1].strip()

        return content.strip()

    def _check_permission(
        self,
        item_permission: PermissionLevel,
        user_permission: PermissionLevel,
    ) -> bool:
        """Check if user has permission to access item.

        Args:
            item_permission: Item's permission level
            user_permission: User's permission level

        Returns:
            True if user can access
        """
        permission_order = {
            PermissionLevel.PUBLIC: 1,
            PermissionLevel.INTERNAL: 2,
            PermissionLevel.CONFIDENTIAL: 3,
            PermissionLevel.RESTRICTED: 4,
        }

        item_level = permission_order.get(item_permission, 99)
        user_level = permission_order.get(user_permission, 0)

        # User can access items at or below their level
        return item_level <= user_level

    def _is_schema_compatible(
        self,
        example_version: str,
        current_version: str,
    ) -> bool:
        """Check if example schema version is compatible with current.

        Args:
            example_version: Version in example
            current_version: Current schema version

        Returns:
            True if compatible
        """
        # Simple version comparison - same major version is compatible
        try:
            ex_parts = example_version.split(".")
            cur_parts = current_version.split(".")

            # Same major version
            if ex_parts[0] == cur_parts[0]:
                return True

            # Within one minor version
            if ex_parts[0] == cur_parts[0] and int(ex_parts[1]) - int(cur_parts[1]) <= 1:
                return True
        except (IndexError, ValueError):
            pass

        return False

    def validate_example_compatibility(
        self,
        example: SQLExample,
        allowed_tables: list[str],
        allowed_columns: list[str],
    ) -> tuple[bool, list[str]]:
        """Validate that an example is compatible with current schema.

        Args:
            example: SQL example to validate
            allowed_tables: Tables the user can access
            allowed_columns: Columns the user can access

        Returns:
            Tuple of (is_compatible, list of issues)
        """
        issues = []

        # Check tables
        for table in example.related_tables:
            if table not in allowed_tables:
                issues.append(f"Table '{table}' not in allowed tables")

        # Note: We don't check columns here as SQL example columns
        # are validated during policy check

        return len(issues) == 0, issues


def create_sql_example_for_kb(
    title: str,
    sql: str,
    description: str,
    domain: str,
    related_metrics: list[str],
    related_tables: list[str],
    version: str = "1.0.0",
    permission_level: PermissionLevel = PermissionLevel.INTERNAL,
) -> dict[str, Any]:
    """Create a SQL example for adding to knowledge base.

    Args:
        title: Example title
        sql: SQL query
        description: Description of the query
        domain: Business domain
        related_metrics: Related metric IDs
        related_tables: Related table names
        version: Schema version
        permission_level: Permission level

    Returns:
        Knowledge item data
    """
    return {
        "source_type": KnowledgeSourceType.SQL_EXAMPLE,
        "title": title,
        "content": f"{description}\n\n```sql\n{sql}\n```",
        "domain_id": domain,
        "semantic_version": version,
        "tags": ["sql", "example", "query", domain],
        "keywords": ["sql", "example", "query", "code"],
        "related_metric_ids": related_metrics,
        "related_table_names": related_tables,
        "permission_level": permission_level,
    }
