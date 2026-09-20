"""Schema Linking - Maps business concepts to physical schema.

This module links:
- Business concepts → Metric / Dimension
- Metric / Dimension → Logical Entity
- Logical Entity → Physical Table / Column
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eiw.nl2sql.contracts import SchemaContext, TableInfo, JoinInfo
from eiw.semantic.v2 import SemanticPackageV2, MetricDefinition, DimensionDefinition
from eiw.observability.otel import trace_span
from eiw.observability.logging import get_structured_logger


logger = get_structured_logger(__name__, "schema_linker")


@dataclass
class BusinessConcept:
    """A business concept from the user's question."""

    text: str
    concept_type: str  # metric, dimension, filter, entity
    confidence: float = 1.0
    alternative_interpretations: list[str] = field(default_factory=list)


@dataclass
class SchemaLink:
    """A link between business concept and schema element."""

    business_concept: BusinessConcept
    target_type: str  # table, column, join
    target_name: str
    target_full_name: str  # e.g., "public.fact_sales.region"
    confidence: float
    reason: str


@dataclass
class SchemaLinkingResult:
    """Result of schema linking."""

    links: list[SchemaLink] = field(default_factory=list)
    linked_tables: list[str] = field(default_factory=list)
    linked_columns: list[str] = field(default_factory=list)
    linked_joins: list[str] = field(default_factory=list)
    unresolved_concepts: list[BusinessConcept] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)


class SchemaLinker:
    """Links business concepts to schema elements.

    This linker:
    1. Extracts business concepts from question
    2. Maps concepts to metrics/dimensions
    3. Maps metrics/dimensions to tables/columns
    4. Identifies required joins
    5. Reports ambiguities
    """

    def __init__(self, semantic_packages: dict[str, SemanticPackageV2]) -> None:
        """Initialize schema linker.

        Args:
            semantic_packages: Dict of domain_id -> SemanticPackageV2
        """
        self._packages = semantic_packages

    def link(
        self,
        question: str,
        domain: str,
        resolved_metrics: list[str],
        resolved_dimensions: list[str],
    ) -> SchemaLinkingResult:
        """Link question to schema elements.

        Args:
            question: Natural language question
            domain: Business domain
            resolved_metrics: Already resolved metric IDs
            resolved_dimensions: Already resolved dimension IDs

        Returns:
            Schema linking result
        """
        with trace_span("nl2sql.schema_link", {
            "domain": domain,
            "question_length": len(question),
            "resolved_metrics": resolved_metrics,
            "resolved_dimensions": resolved_dimensions,
        }):
            pkg = self._packages.get(domain)
            if not pkg:
                logger.warning(f"No semantic package for domain: {domain}")
                return SchemaLinkingResult()

            result = SchemaLinkingResult()

            # Link metrics
            for metric_id in resolved_metrics:
                self._link_metric(pkg, metric_id, result)

            # Link dimensions
            for dim_id in resolved_dimensions:
                self._link_dimension(pkg, dim_id, result)

            # Extract and link additional concepts from question
            self._extract_additional_concepts(question, pkg, result)

            # Identify required joins
            self._identify_joins(pkg, result)

            logger.info(
                f"Schema linking complete: {len(result.linked_tables)} tables, "
                f"{len(result.linked_columns)} columns, {len(result.linked_joins)} joins",
                extra={
                    "linked_tables": result.linked_tables,
                    "linked_columns": result.linked_columns,
                    "ambiguities": result.ambiguities,
                }
            )

            return result

    def _link_metric(
        self,
        pkg: SemanticPackageV2,
        metric_id: str,
        result: SchemaLinkingResult,
    ) -> None:
        """Link a metric to schema elements.

        Args:
            pkg: Semantic package
            metric_id: Metric ID
            result: Result to update
        """
        try:
            metric = pkg.metric(metric_id)
        except KeyError:
            logger.warning(f"Unknown metric: {metric_id}")
            return

        # Link to source table
        self._add_table_link(
            business_text=metric_id,
            concept_type="metric",
            table_name=metric.source_table,
            confidence=1.0,
            reason=f"Source table for metric '{metric.name}'",
            result=result,
        )

        # Link to source columns
        for col_name in metric.source_columns:
            self._add_column_link(
                business_text=metric_id,
                concept_type="metric",
                table_name=metric.source_table,
                column_name=col_name,
                confidence=1.0,
                reason=f"Source column for metric '{metric.name}'",
                result=result,
            )

        # Add join paths
        for join_path in metric.allowed_join_paths:
            result.linked_joins.extend(join_path.intermediate_tables)

    def _link_dimension(
        self,
        pkg: SemanticPackageV2,
        dim_id: str,
        result: SchemaLinkingResult,
    ) -> None:
        """Link a dimension to schema elements.

        Args:
            pkg: Semantic package
            dim_id: Dimension ID
            result: Result to update
        """
        try:
            dimension = pkg.dimension(dim_id)
        except KeyError:
            logger.warning(f"Unknown dimension: {dim_id}")
            return

        # Link to source table
        self._add_table_link(
            business_text=dim_id,
            concept_type="dimension",
            table_name=dimension.source_table,
            confidence=1.0,
            reason=f"Source table for dimension '{dimension.name}'",
            result=result,
        )

        # Link to source column
        self._add_column_link(
            business_text=dim_id,
            concept_type="dimension",
            table_name=dimension.source_table,
            column_name=dimension.source_column,
            confidence=1.0,
            reason=f"Source column for dimension '{dimension.name}'",
            result=result,
        )

        # Add join paths
        for join_path in dimension.join_paths:
            if join_path not in result.linked_joins:
                result.linked_joins.append(join_path)

    def _extract_additional_concepts(
        self,
        question: str,
        pkg: SemanticPackageV2,
        result: SchemaLinkingResult,
    ) -> None:
        """Extract additional concepts from question text.

        Args:
            question: User question
            pkg: Semantic package
            result: Result to update
        """
        question_lower = question.lower()
        words = set(question_lower.split())

        # Check for metric aliases
        for metric in pkg.metrics:
            for alias in metric.aliases:
                if alias.lower() in question_lower:
                    if metric.id not in result.linked_tables:
                        self._link_metric(pkg, metric.id, result)

        # Check for dimension aliases
        for dim in pkg.dimensions:
            for alias in dim.aliases:
                if alias.lower() in question_lower:
                    if dim.id not in result.linked_tables:
                        self._link_dimension(pkg, dim.id, result)

        # Check for common terms
        common_terms = {
            "revenue": "revenue",
            "sales": "sales",
            "profit": "gross_profit",
            "region": "region",
            "product": "product_category",
            "time": "fiscal_period",
            "date": "fiscal_period",
        }

        for term, metric_id in common_terms.items():
            if term in words:
                if metric_id not in result.linked_tables:
                    try:
                        pkg.metric(metric_id)
                        self._link_metric(pkg, metric_id, result)
                    except KeyError:
                        try:
                            pkg.dimension(metric_id)
                            self._link_dimension(pkg, metric_id, result)
                        except KeyError:
                            pass

    def _identify_joins(
        self,
        pkg: SemanticPackageV2,
        result: SchemaLinkingResult,
    ) -> None:
        """Identify required joins between linked tables.

        Args:
            pkg: Semantic package
            result: Result to update
        """
        # Build adjacency list of valid joins
        valid_joins: dict[str, set[str]] = {}

        for metric in pkg.metrics:
            valid_joins.setdefault(metric.source_table, set())
            for join_path in metric.allowed_join_paths:
                for intermediate in join_path.intermediate_tables:
                    valid_joins[metric.source_table].add(intermediate)
                # Also add the target tables
                for jc in join_path.join_conditions:
                    # Extract table names from join conditions
                    if " JOIN " in jc.upper():
                        for table in pkg.package.id.split():  # Simplified
                            if table in jc:
                                valid_joins[metric.source_table].add(table)

        # Check if all linked tables are reachable
        if not result.linked_tables:
            return

        # Add required dimension tables
        for dim in pkg.dimensions:
            if dim.source_table in result.linked_tables:
                # Check if dimension table needs join
                for metric_table in result.linked_tables:
                    if metric_table != dim.source_table:
                        # Check if there's a join path
                        joins = valid_joins.get(metric_table, set())
                        if dim.source_table not in joins and dim.source_table not in result.linked_tables:
                            # Add as potential join (will be validated later)
                            if dim.source_table not in result.linked_joins:
                                result.linked_joins.append(dim.source_table)

    def _add_table_link(
        self,
        business_text: str,
        concept_type: str,
        table_name: str,
        confidence: float,
        reason: str,
        result: SchemaLinkingResult,
    ) -> None:
        """Add a table link.

        Args:
            business_text: Business concept text
            concept_type: Type of concept
            table_name: Table name
            confidence: Confidence score
            reason: Reason for link
            result: Result to update
        """
        if table_name not in result.linked_tables:
            result.linked_tables.append(table_name)

        result.links.append(SchemaLink(
            business_concept=BusinessConcept(
                text=business_text,
                concept_type=concept_type,
                confidence=confidence,
            ),
            target_type="table",
            target_name=table_name,
            target_full_name=table_name,
            confidence=confidence,
            reason=reason,
        ))

    def _add_column_link(
        self,
        business_text: str,
        concept_type: str,
        table_name: str,
        column_name: str,
        confidence: float,
        reason: str,
        result: SchemaLinkingResult,
    ) -> None:
        """Add a column link.

        Args:
            business_text: Business concept text
            concept_type: Type of concept
            table_name: Table name
            column_name: Column name
            confidence: Confidence score
            reason: Reason for link
            result: Result to update
        """
        full_name = f"{table_name}.{column_name}"
        if full_name not in result.linked_columns:
            result.linked_columns.append(full_name)

        result.links.append(SchemaLink(
            business_concept=BusinessConcept(
                text=business_text,
                concept_type=concept_type,
                confidence=confidence,
            ),
            target_type="column",
            target_name=column_name,
            target_full_name=full_name,
            confidence=confidence,
            reason=reason,
        ))
