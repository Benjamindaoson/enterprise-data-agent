"""Permission-aware hybrid schema retrieval for governed NL2SQL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eiw.nl2sql.contracts import ColumnInfo, JoinInfo, SchemaContext, TableInfo
from eiw.nl2sql.retrieval import HybridRetrievalService, RetrievalCandidate
from eiw.observability.logging import get_structured_logger
from eiw.observability.otel import trace_span
from eiw.semantic.v2 import DimensionDefinition, MetricDefinition, SemanticPackageV2

logger = get_structured_logger(__name__, "schema_retriever")


class SchemaRetriever:
    """Retrieve governed schema context without creating a second NL2SQL path.

    Explicit semantic resolutions are authoritative and protected. Hybrid
    retrieval only supplements unresolved context from the same semantic package.
    """

    def __init__(
        self,
        semantic_packages: dict[str, SemanticPackageV2],
        retrieval: HybridRetrievalService | None = None,
    ) -> None:
        self._packages = semantic_packages
        self._retrieval = retrieval or HybridRetrievalService()

    def retrieve(
        self,
        domain: str,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        user_roles: list[str] | None = None,
        business_context: dict[str, Any] | None = None,
        question: str = "",
    ) -> SchemaContext:
        """Return a permission-aware, budgeted schema context."""

        metrics = list(dict.fromkeys(metrics or []))
        dimensions = list(dict.fromkeys(dimensions or []))
        user_roles = user_roles or []
        business_context = business_context or {}

        with trace_span(
            "nl2sql.schema_retrieve",
            {
                "domain": domain,
                "metrics_count": len(metrics),
                "dimensions_count": len(dimensions),
                "user_roles": user_roles,
            },
        ):
            package = self._packages.get(domain)
            if not package:
                logger.warning(f"No semantic package for domain: {domain}")
                return SchemaContext(domain=domain)

            selected_metrics = metrics.copy()
            selected_dimensions = dimensions.copy()
            retrieval_hits = []

            if question:
                candidates = self._semantic_candidates(
                    package,
                    protected_metrics=set(metrics),
                    protected_dimensions=set(dimensions),
                )
                mode = str(business_context.get("retrieval_mode", "hybrid_rerank"))
                candidate_budget = int(
                    business_context.get("schema_candidate_budget", 8)
                )
                candidate_budget = max(1, min(candidate_budget, 32))
                retrieval_hits = self._retrieval.retrieve(
                    question,
                    candidates,
                    top_k=candidate_budget,
                    mode=mode,
                )
                for hit in retrieval_hits:
                    object_type, object_id = hit.candidate.object_id.split(":", 1)
                    if object_type == "metric" and object_id not in selected_metrics:
                        selected_metrics.append(object_id)
                    elif (
                        object_type == "dimension"
                        and object_id not in selected_dimensions
                    ):
                        selected_dimensions.append(object_id)
            else:
                mode = "explicit_only"
                candidate_budget = len(metrics) + len(dimensions)

            schema = SchemaContext(domain=domain)

            for metric_id in selected_metrics:
                try:
                    self._add_metric_table(package.metric(metric_id), schema)
                except KeyError:
                    logger.warning(f"Unknown metric: {metric_id}")

            for dimension_id in selected_dimensions:
                try:
                    self._add_dimension_table(package.dimension(dimension_id), schema)
                except KeyError:
                    logger.warning(f"Unknown dimension: {dimension_id}")

            self._add_joins(package, schema)
            self._filter_by_permissions(schema, user_roles)

            schema.retrieval_trace = {
                "mode": mode,
                "candidate_budget": candidate_budget,
                "protected_metrics": metrics,
                "protected_dimensions": dimensions,
                "selected_metrics": selected_metrics,
                "selected_dimensions": selected_dimensions,
                "hits": [
                    {
                        "object_id": hit.candidate.object_id,
                        "score": round(hit.score, 8),
                        "source_ranks": dict(hit.source_ranks),
                    }
                    for hit in retrieval_hits
                ],
                "selected_tables": sorted(schema.tables),
            }

            logger.info(
                f"Schema retrieved: {len(schema.tables)} tables, "
                f"{len(schema.joins)} joins",
                extra={
                    "domain": domain,
                    "table_count": len(schema.tables),
                    "join_count": len(schema.joins),
                    "retrieval_mode": mode,
                },
            )
            return schema

    @staticmethod
    def _semantic_candidates(
        package: SemanticPackageV2,
        *,
        protected_metrics: set[str],
        protected_dimensions: set[str],
    ) -> list[RetrievalCandidate]:
        candidates: list[RetrievalCandidate] = []

        for metric in package.metrics:
            text = " ".join(
                part
                for part in (
                    metric.id,
                    metric.name,
                    " ".join(metric.aliases),
                    metric.description,
                    metric.business_context or "",
                    metric.source_table,
                    " ".join(metric.source_columns),
                )
                if part
            )
            candidates.append(
                RetrievalCandidate(
                    object_id=f"metric:{metric.id}",
                    object_type="metric",
                    text=text,
                    table_name=metric.source_table,
                    protected=metric.id in protected_metrics,
                    metadata={"name": metric.name},
                )
            )

        for dimension in package.dimensions:
            text = " ".join(
                part
                for part in (
                    dimension.id,
                    dimension.name,
                    " ".join(dimension.aliases),
                    dimension.description,
                    dimension.source_table,
                    dimension.source_column,
                )
                if part
            )
            candidates.append(
                RetrievalCandidate(
                    object_id=f"dimension:{dimension.id}",
                    object_type="dimension",
                    text=text,
                    table_name=dimension.source_table,
                    column_name=dimension.source_column,
                    protected=dimension.id in protected_dimensions,
                    metadata={"name": dimension.name},
                )
            )
        return candidates

    @staticmethod
    def _merge_columns(table: TableInfo, columns: list[ColumnInfo]) -> None:
        existing = {column.name for column in table.columns}
        for column in columns:
            if column.name not in existing:
                table.columns.append(column)
                existing.add(column.name)

    def _add_metric_table(
        self,
        metric: MetricDefinition,
        schema: SchemaContext,
    ) -> None:
        columns = self._get_columns_for_metric(metric)
        existing = schema.tables.get(metric.source_table)
        if existing is not None:
            self._merge_columns(existing, columns)
            return

        schema.tables[metric.source_table] = TableInfo(
            name=metric.source_table,
            description=f"Source table for metric: {metric.name}",
            columns=columns,
            classification=metric.classification.value,
            is_sensitive=metric.classification.value
            in ("CONFIDENTIAL", "RESTRICTED"),
        )

    def _add_dimension_table(
        self,
        dimension: DimensionDefinition,
        schema: SchemaContext,
    ) -> None:
        column = ColumnInfo(
            name=dimension.source_column,
            data_type="UNKNOWN",
            description=f"Source column for dimension: {dimension.name}",
            is_sensitive=dimension.classification.value
            in ("CONFIDENTIAL", "RESTRICTED"),
            policy_tags=dimension.policy_tags,
        )
        existing = schema.tables.get(dimension.source_table)
        if existing is not None:
            self._merge_columns(existing, [column])
            return

        schema.tables[dimension.source_table] = TableInfo(
            name=dimension.source_table,
            description=f"Source table for dimension: {dimension.name}",
            columns=[column],
            classification=dimension.classification.value,
            is_sensitive=dimension.classification.value
            in ("CONFIDENTIAL", "RESTRICTED"),
        )

    @staticmethod
    def _get_columns_for_metric(metric: MetricDefinition) -> list[ColumnInfo]:
        columns = [
            ColumnInfo(
                name=column_name,
                data_type="UNKNOWN",
                description=f"Source column for {metric.name}",
            )
            for column_name in metric.source_columns
        ]
        if not columns and metric.formula.expression:
            columns.append(
                ColumnInfo(
                    name="*",
                    data_type="ANY",
                    description=f"Formula-backed columns for {metric.name}",
                )
            )
        return columns

    @staticmethod
    def _add_joins(
        package: SemanticPackageV2,
        schema: SchemaContext,
    ) -> None:
        selected_tables = set(schema.tables)
        for metric in package.metrics:
            if metric.source_table not in selected_tables:
                continue
            for join_path in metric.allowed_join_paths:
                for table in join_path.intermediate_tables:
                    if table not in schema.tables:
                        schema.tables[table] = TableInfo(
                            name=table,
                            description="Intermediate governed join table",
                        )

        for policy in package.join_policies:
            for path in policy.get("paths", []):
                from_table = path.get("from", "")
                to_table = path.get("to", "")
                if not from_table or not to_table:
                    continue
                if from_table not in schema.tables and to_table not in schema.tables:
                    continue
                join = JoinInfo(
                    from_table=from_table,
                    to_table=to_table,
                    from_column=path.get("from_column", "id"),
                    to_column=path.get("to_column", "id"),
                    join_type=path.get("type", "INNER"),
                    cardinality=path.get("cardinality", "many_to_one"),
                )
                if join not in schema.joins:
                    schema.joins.append(join)

    @staticmethod
    def _filter_by_permissions(
        schema: SchemaContext,
        user_roles: list[str],
    ) -> None:
        restricted_tables = {"admin_only", "system_config", "audit_log"}
        if "admin" in user_roles or "data_admin" in user_roles:
            return
        for table_name in list(schema.tables):
            if table_name in restricted_tables:
                del schema.tables[table_name]


@dataclass
class SchemaRetrievalRequest:
    domain: str
    metrics: list[str]
    dimensions: list[str]
    user_roles: list[str]
    business_context: dict[str, Any] | None = None
    question: str = ""


@dataclass
class SchemaRetrievalResult:
    schema: SchemaContext
    tables_included: list[str]
    tables_excluded: list[str]
    joins_included: list[str]
    permission_filtered: bool = False
