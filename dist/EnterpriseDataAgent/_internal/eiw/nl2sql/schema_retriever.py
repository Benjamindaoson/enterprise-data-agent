"""Permission-aware Schema Retrieval for NL2SQL.

This module retrieves relevant schema elements based on:
- Domain
- Resolved metrics and dimensions
- User permissions and roles
- Task context
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eiw.nl2sql.contracts import (
    SchemaContext,
    TableInfo,
    ColumnInfo,
    JoinInfo,
)
from eiw.semantic.v2 import (
    SemanticPackageV2,
    MetricDefinition,
    DimensionDefinition,
)
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "schema_retriever")


class SchemaRetriever:
    """Retrieves permission-aware schema for NL2SQL.

    This retriever:
    1. Loads schema from semantic packages
    2. Filters based on user permissions
    3. Includes only tables/columns relevant to the query
    4. Respects RBAC policies
    """

    def __init__(self, semantic_packages: dict[str, SemanticPackageV2]) -> None:
        """Initialize schema retriever.

        Args:
            semantic_packages: Dict of domain_id -> SemanticPackageV2
        """
        self._packages = semantic_packages

    def retrieve(
        self,
        domain: str,
        metrics: list[str],
        dimensions: list[str],
        user_roles: list[str],
        business_context: dict[str, Any] | None = None,
    ) -> SchemaContext:
        """Retrieve schema for the given context.

        Args:
            domain: Business domain
            metrics: Requested metric IDs
            dimensions: Requested dimension IDs
            user_roles: User roles for permission filtering
            business_context: Additional business context

        Returns:
            Schema context with only accessible and relevant elements
        """
        with trace_span("nl2sql.schema_retrieve", {
            "domain": domain,
            "metrics_count": len(metrics),
            "dimensions_count": len(dimensions),
            "user_roles": user_roles,
        }):
            # Get the semantic package for this domain
            pkg = self._packages.get(domain)
            if not pkg:
                logger.warning(f"No semantic package for domain: {domain}")
                return SchemaContext(domain=domain)

            # Build schema context
            schema = SchemaContext(domain=domain)

            # Add tables based on metrics
            for metric_id in metrics:
                try:
                    metric = pkg.metric(metric_id)
                    self._add_metric_table(metric, schema, user_roles)
                except KeyError:
                    logger.warning(f"Unknown metric: {metric_id}")

            # Add tables based on dimensions
            for dim_id in dimensions:
                try:
                    dim = pkg.dimension(dim_id)
                    self._add_dimension_table(dim, schema, user_roles)
                except KeyError:
                    logger.warning(f"Unknown dimension: {dim_id}")

            # Add joins based on metric/dimension relationships
            self._add_joins(pkg, schema)

            # Filter by permissions
            self._filter_by_permissions(schema, user_roles)

            logger.info(
                f"Schema retrieved: {len(schema.tables)} tables, {len(schema.joins)} joins",
                extra={
                    "domain": domain,
                    "table_count": len(schema.tables),
                    "join_count": len(schema.joins),
                }
            )

            return schema

    def _add_metric_table(
        self,
        metric: MetricDefinition,
        schema: SchemaContext,
        user_roles: list[str],
    ) -> None:
        """Add table for a metric.

        Args:
            metric: Metric definition
            schema: Schema context to update
            user_roles: User roles
        """
        table_name = metric.source_table

        # Check if already added
        if table_name in schema.tables:
            return

        # Create table info
        table = TableInfo(
            name=table_name,
            description=f"Source table for metric: {metric.name}",
            columns=self._get_columns_for_metric(metric),
            classification=metric.classification.value,
            is_sensitive=metric.classification.value in ("CONFIDENTIAL", "RESTRICTED"),
        )

        schema.tables[table_name] = table

    def _add_dimension_table(
        self,
        dimension: DimensionDefinition,
        schema: SchemaContext,
        user_roles: list[str],
    ) -> None:
        """Add table for a dimension.

        Args:
            dimension: Dimension definition
            schema: Schema context to update
            user_roles: User roles
        """
        table_name = dimension.source_table

        # Check if already added
        if table_name in schema.tables:
            return

        # Create table info
        table = TableInfo(
            name=table_name,
            description=f"Source table for dimension: {dimension.name}",
            columns=[
                ColumnInfo(
                    name=dimension.source_column,
                    data_type="UNKNOWN",
                    description=f"Source column for dimension: {dimension.name}",
                    is_sensitive=dimension.classification.value in ("CONFIDENTIAL", "RESTRICTED"),
                    policy_tags=dimension.policy_tags,
                )
            ],
            classification=dimension.classification.value,
            is_sensitive=dimension.classification.value in ("CONFIDENTIAL", "RESTRICTED"),
        )

        schema.tables[table_name] = table

    def _get_columns_for_metric(self, metric: MetricDefinition) -> list[ColumnInfo]:
        """Get columns for a metric.

        Args:
            metric: Metric definition

        Returns:
            List of column info
        """
        columns = []

        # Add source columns from formula
        for col_name in metric.source_columns:
            columns.append(ColumnInfo(
                name=col_name,
                data_type="UNKNOWN",
                description=f"Source column for {metric.name}",
            ))

        # Also add expression-derived columns
        if metric.formula.expression:
            # This is simplified - in production would parse SQL
            columns.append(ColumnInfo(
                name="*",
                data_type="ANY",
                description=f"All columns from {metric.source_table}",
            ))

        return columns

    def _add_joins(
        self,
        pkg: SemanticPackageV2,
        schema: SchemaContext,
    ) -> None:
        """Add valid joins based on package configuration.

        Args:
            pkg: Semantic package
            schema: Schema context to update
        """
        # Get joins from metric definitions
        for metric in pkg.metrics:
            for join_path in metric.allowed_join_paths:
                # Add intermediate tables as needed
                for intermediate_table in join_path.intermediate_tables:
                    if intermediate_table not in schema.tables:
                        schema.tables[intermediate_table] = TableInfo(
                            name=intermediate_table,
                            description=f"Intermediate join table",
                        )

        # Add default joins from join policies
        for policy in pkg.join_policies:
            paths = policy.get("paths", [])
            for path in paths:
                join = JoinInfo(
                    from_table=path.get("from", ""),
                    to_table=path.get("to", ""),
                    from_column="id",
                    to_column="id",
                    join_type=path.get("type", "INNER"),
                    cardinality="many_to_one",
                )
                # Avoid duplicates
                if join not in schema.joins:
                    schema.joins.append(join)

    def _filter_by_permissions(
        self,
        schema: SchemaContext,
        user_roles: list[str],
    ) -> None:
        """Filter schema elements based on user permissions.

        Args:
            schema: Schema context to filter
            user_roles: User roles
        """
        # Remove restricted tables from non-admin roles
        restricted_tables = {"admin_only", "system_config", "audit_log"}

        if "admin" not in user_roles and "data_admin" not in user_roles:
            for table_name in list(schema.tables.keys()):
                if table_name in restricted_tables:
                    del schema.tables[table_name]


@dataclass
class SchemaRetrievalRequest:
    """Request for schema retrieval."""

    domain: str
    metrics: list[str]
    dimensions: list[str]
    user_roles: list[str]
    business_context: dict[str, Any] | None = None


@dataclass
class SchemaRetrievalResult:
    """Result of schema retrieval."""

    schema: SchemaContext
    tables_included: list[str]
    tables_excluded: list[str]
    joins_included: list[str]
    permission_filtered: bool = False
