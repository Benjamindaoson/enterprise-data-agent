"""Governed PostgreSQL enterprise connector and domain runtime."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from eiw.semantic.package import (
    Availability,
    DimensionDefinition,
    MetricDefinition,
    PackageIdentity,
    SemanticPackage,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

DomainEventCallback = Callable[[Any], None]


class PostgresConnectorConfig(BaseModel):
    allowed_schemas: list[str] = Field(default_factory=lambda: ["public"])
    allowed_tables: list[str] = Field(default_factory=list)
    denied_columns: list[str] = Field(default_factory=list)
    max_rows: int = Field(default=200, ge=1, le=5000)
    statement_timeout_ms: int = Field(default=15000, ge=100, le=300000)


class PostgresMetricSpec(BaseModel):
    id: str
    label: str
    column: str
    aggregation: Literal["sum", "avg", "count", "count_distinct"] = "sum"
    unit: str = "value"
    description: str | None = None


class PostgresDimensionSpec(BaseModel):
    id: str
    label: str
    column: str
    grain: str | None = None


class PostgresSemanticConfig(BaseModel):
    package_id: str
    version: str = "1.0.0"
    title: str
    schema_name: str = "public"
    fact_table: str
    timezone: str = "UTC"
    currency: str = "USD"
    metrics: list[PostgresMetricSpec]
    dimensions: list[PostgresDimensionSpec] = Field(default_factory=list)
    role_metric_allowlist: dict[str, list[str]] = Field(default_factory=dict)


class CatalogColumn(BaseModel):
    name: str
    data_type: str
    nullable: bool
    primary_key: bool = False


class CatalogTable(BaseModel):
    schema_name: str
    table_name: str
    columns: list[CatalogColumn]
    foreign_keys: list[dict[str, Any]] = Field(default_factory=list)


class PostgresCatalog(BaseModel):
    source: str
    tables: list[CatalogTable]
    catalog_hash: str


class PostgresAnalysisRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)
    role: str = Field(default="analyst", min_length=1, max_length=128)
    top_k: int = Field(default=20, ge=1, le=500)


class PostgresAnalysisResponse(BaseModel):
    task_id: str
    status: str
    question: str
    metric_id: str
    dimension_ids: list[str]
    rows: list[dict[str, Any]]
    evidence: dict[str, Any]
    report: dict[str, Any]
    semantic_package: dict[str, str]


def load_postgres_semantic_config(path: Path) -> PostgresSemanticConfig:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PostgresSemanticConfig.model_validate(parsed)


class PostgresEnterpriseConnector:
    """Read-only PostgreSQL connector with introspection and semantic execution."""

    def __init__(
        self,
        database_url: str,
        *,
        config: PostgresConnectorConfig | None = None,
    ) -> None:
        self.engine: Engine = create_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
        )
        self.config = config or PostgresConnectorConfig()

    def ping(self) -> bool:
        with self.engine.connect() as connection:
            return bool(connection.execute(text("SELECT 1")).scalar_one() == 1)

    def introspect(self) -> PostgresCatalog:
        inspector = inspect(self.engine)
        tables: list[CatalogTable] = []
        allowed_tables = set(self.config.allowed_tables)
        denied_columns = set(self.config.denied_columns)

        for schema_name in self.config.allowed_schemas:
            self._validate_identifier(schema_name)
            names = sorted(inspector.get_table_names(schema=schema_name))
            for table_name in names:
                self._validate_identifier(table_name)
                if allowed_tables and table_name not in allowed_tables:
                    continue
                primary = inspector.get_pk_constraint(
                    table_name,
                    schema=schema_name,
                ).get("constrained_columns") or []
                columns = [
                    CatalogColumn(
                        name=str(column["name"]),
                        data_type=str(column["type"]),
                        nullable=bool(column.get("nullable", True)),
                        primary_key=str(column["name"]) in primary,
                    )
                    for column in inspector.get_columns(
                        table_name,
                        schema=schema_name,
                    )
                    if str(column["name"]) not in denied_columns
                ]
                foreign_keys = [
                    {
                        "columns": list(item.get("constrained_columns") or []),
                        "referred_schema": item.get("referred_schema"),
                        "referred_table": item.get("referred_table"),
                        "referred_columns": list(item.get("referred_columns") or []),
                    }
                    for item in inspector.get_foreign_keys(
                        table_name,
                        schema=schema_name,
                    )
                ]
                tables.append(
                    CatalogTable(
                        schema_name=schema_name,
                        table_name=table_name,
                        columns=columns,
                        foreign_keys=foreign_keys,
                    )
                )

        source = self.engine.url.render_as_string(hide_password=True)
        canonical = json.dumps(
            [table.model_dump(mode="json") for table in tables],
            sort_keys=True,
            separators=(",", ":"),
        )
        return PostgresCatalog(
            source=source,
            tables=tables,
            catalog_hash=sha256(canonical.encode("utf-8")).hexdigest(),
        )

    def build_semantic_package(
        self,
        semantic: PostgresSemanticConfig,
        *,
        catalog: PostgresCatalog | None = None,
    ) -> SemanticPackage:
        catalog = catalog or self.introspect()
        table = self._find_table(
            catalog,
            semantic.schema_name,
            semantic.fact_table,
        )
        available_columns = {column.name for column in table.columns}
        denied = set(self.config.denied_columns)

        metric_definitions: list[MetricDefinition] = []
        for metric in semantic.metrics:
            self._validate_identifier(metric.column)
            if metric.column not in available_columns or metric.column in denied:
                raise ValueError(
                    f"metric column is unavailable or denied: {metric.column}"
                )
            metric_definitions.append(
                MetricDefinition(
                    id=metric.id,
                    label=metric.label,
                    expression=self._metric_expression(semantic, metric),
                    unit=metric.unit,
                    availability=Availability(
                        **{"from": date(1900, 1, 1), "to": date(2100, 1, 1)}
                    ),
                    description=metric.description,
                )
            )

        dimension_definitions: list[DimensionDefinition] = []
        for dimension in semantic.dimensions:
            self._validate_identifier(dimension.column)
            if dimension.column not in available_columns or dimension.column in denied:
                raise ValueError(
                    f"dimension column is unavailable or denied: {dimension.column}"
                )
            dimension_definitions.append(
                DimensionDefinition(
                    id=dimension.id,
                    label=dimension.label,
                    source=(
                        f"{semantic.schema_name}.{semantic.fact_table}."
                        f"{dimension.column}"
                    ),
                    grain=dimension.grain or dimension.id,
                    attributes=[dimension.column],
                )
            )

        access_policies = {
            role: {"allow": list(metric_ids)}
            for role, metric_ids in semantic.role_metric_allowlist.items()
        }
        if not access_policies:
            access_policies = {
                "analyst": {"allow": [metric.id for metric in semantic.metrics]}
            }

        identity = PackageIdentity(
            id=semantic.package_id,
            version=semantic.version,
            title=semantic.title,
            timezone=semantic.timezone,
            currency=semantic.currency,
            source_snapshot_alias=catalog.catalog_hash[:12],
            default_snapshot=catalog.catalog_hash,
            description=(
                "Generated from a governed PostgreSQL catalog and explicit "
                "enterprise semantic configuration."
            ),
        )
        package = SemanticPackage(
            package=identity,
            facts=[
                {
                    "id": semantic.fact_table,
                    "source": f"{semantic.schema_name}.{semantic.fact_table}",
                    "grain": "configured-fact-table",
                }
            ],
            metrics=metric_definitions,
            dimensions=dimension_definitions,
            join_policies=[],
            business_rules=[
                {
                    "id": "read_only_connector",
                    "description": "Connector analysis is read-only and bounded by role permissions.",
                }
            ],
            quality_rules=[
                {
                    "id": "catalog_binding",
                    "description": f"Semantic package is bound to catalog {catalog.catalog_hash}.",
                }
            ],
            access_policies=access_policies,
        )
        semantic_identity = {
            "config": semantic.model_dump(mode="json"),
            "catalog_hash": catalog.catalog_hash,
        }
        content_hash = sha256(
            json.dumps(
                semantic_identity,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return package.model_copy(update={"content_hash": content_hash})

    def analyze(
        self,
        request: PostgresAnalysisRequest,
        *,
        semantic: PostgresSemanticConfig,
        package: SemanticPackage,
        catalog: PostgresCatalog,
    ) -> PostgresAnalysisResponse:
        metric = self._resolve_metric(request.question, semantic)
        dimensions = self._resolve_dimensions(request.question, semantic)
        self._check_permission(request.role, metric.id, package)
        self._check_execution_columns(metric, dimensions)

        limit = min(request.top_k, self.config.max_rows)
        sql = self._compile_sql(semantic, metric, dimensions, limit=limit)
        rows = self._execute_readonly(sql)
        evidence = self._evidence(
            request=request,
            sql=sql,
            rows=rows,
            package=package,
            catalog=catalog,
        )
        report = self._report(metric, dimensions, rows, evidence)
        return PostgresAnalysisResponse(
            task_id=f"pg-{evidence['evidence_id'][:12]}",
            status="COMPLETED",
            question=request.question,
            metric_id=metric.id,
            dimension_ids=[dimension.id for dimension in dimensions],
            rows=rows,
            evidence=evidence,
            report=report,
            semantic_package={
                "id": package.package.id,
                "version": package.package.version,
                "content_hash": package.content_hash,
            },
        )

    def _resolve_metric(
        self,
        question: str,
        semantic: PostgresSemanticConfig,
    ) -> PostgresMetricSpec:
        lowered = question.lower()
        for metric in semantic.metrics:
            if metric.id.lower() in lowered or metric.label.lower() in lowered:
                return metric
        if len(semantic.metrics) == 1:
            return semantic.metrics[0]
        raise ValueError(
            "Question does not identify a governed metric; use a metric id or label."
        )

    @staticmethod
    def _resolve_dimensions(
        question: str,
        semantic: PostgresSemanticConfig,
    ) -> list[PostgresDimensionSpec]:
        lowered = question.lower()
        return [
            dimension
            for dimension in semantic.dimensions
            if dimension.id.lower() in lowered or dimension.label.lower() in lowered
        ]

    @staticmethod
    def _check_permission(
        role: str,
        metric_id: str,
        package: SemanticPackage,
    ) -> None:
        policy = package.access_policies.get(role)
        if policy is None:
            raise PermissionError(f"unknown or unauthorized role: {role}")
        allowed = set(policy.get("allow", []))
        if metric_id not in allowed and "*" not in allowed:
            raise PermissionError(
                f"role {role} is not allowed to access metric {metric_id}"
            )

    def _check_execution_columns(
        self,
        metric: PostgresMetricSpec,
        dimensions: list[PostgresDimensionSpec],
    ) -> None:
        denied = set(self.config.denied_columns)
        requested = {metric.column, *(dimension.column for dimension in dimensions)}
        blocked = sorted(requested & denied)
        if blocked:
            raise PermissionError(f"query references denied columns: {blocked}")

    def _compile_sql(
        self,
        semantic: PostgresSemanticConfig,
        metric: PostgresMetricSpec,
        dimensions: list[PostgresDimensionSpec],
        *,
        limit: int,
    ) -> str:
        schema = self._quote(semantic.schema_name)
        table = self._quote(semantic.fact_table)
        metric_column = self._quote(metric.column)
        metric_sql = {
            "sum": f"SUM({metric_column})",
            "avg": f"AVG({metric_column})",
            "count": f"COUNT({metric_column})",
            "count_distinct": f"COUNT(DISTINCT {metric_column})",
        }[metric.aggregation]
        metric_alias = self._quote(metric.id)

        if not dimensions:
            return (
                f"SELECT {metric_sql} AS {metric_alias} "
                f"FROM {schema}.{table} LIMIT {int(limit)}"
            )

        dimension_sql = [
            (self._quote(dimension.column), self._quote(dimension.id))
            for dimension in dimensions
        ]
        selects = ", ".join(
            [*(f"{column} AS {alias}" for column, alias in dimension_sql), f"{metric_sql} AS {metric_alias}"]
        )
        groups = ", ".join(column for column, _ in dimension_sql)
        return (
            f"SELECT {selects} FROM {schema}.{table} "
            f"GROUP BY {groups} ORDER BY {metric_alias} DESC NULLS LAST "
            f"LIMIT {int(limit)}"
        )

    def _execute_readonly(self, sql: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection, connection.begin():
            if self.engine.dialect.name == "postgresql":
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(
                    text(
                        f"SET LOCAL statement_timeout = "
                        f"{int(self.config.statement_timeout_ms)}"
                    )
                )
            rows = connection.execute(text(sql)).mappings().all()
        return [dict(row) for row in rows]

    def _evidence(
        self,
        *,
        request: PostgresAnalysisRequest,
        sql: str,
        rows: list[dict[str, Any]],
        package: SemanticPackage,
        catalog: PostgresCatalog,
    ) -> dict[str, Any]:
        fingerprint_payload = json.dumps(
            {
                "question": request.question,
                "sql": sql,
                "rows": rows,
                "semantic_hash": package.content_hash,
                "catalog_hash": catalog.catalog_hash,
            },
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        evidence_id = sha256(fingerprint_payload.encode("utf-8")).hexdigest()
        return {
            "evidence_id": evidence_id,
            "connector": "postgresql",
            "source": catalog.source,
            "catalog_hash": catalog.catalog_hash,
            "semantic_package_id": package.package.id,
            "semantic_package_version": package.package.version,
            "semantic_content_hash": package.content_hash,
            "sql": sql,
            "row_count": len(rows),
            "captured_at": datetime.now(UTC).isoformat(),
            "read_only": True,
        }

    @staticmethod
    def _report(
        metric: PostgresMetricSpec,
        dimensions: list[PostgresDimensionSpec],
        rows: list[dict[str, Any]],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        top = rows[0] if rows else None
        if top is None:
            summary = f"No rows were returned for governed metric {metric.label}."
        elif dimensions:
            labels = ", ".join(
                f"{dimension.label}={top.get(dimension.id)}"
                for dimension in dimensions
            )
            summary = (
                f"Top observed {metric.label} result: {labels}; "
                f"{metric.label}={top.get(metric.id)}."
            )
        else:
            summary = f"Observed {metric.label}: {top.get(metric.id)}."
        return {
            "title": "Enterprise PostgreSQL Analysis",
            "executive_summary": [summary],
            "top_rows": rows,
            "evidence_id": evidence["evidence_id"],
            "limitations": [
                "This report describes governed database observations; it does not infer causality."
            ],
        }

    def _metric_expression(
        self,
        semantic: PostgresSemanticConfig,
        metric: PostgresMetricSpec,
    ) -> str:
        self._validate_identifier(semantic.schema_name)
        self._validate_identifier(semantic.fact_table)
        self._validate_identifier(metric.column)
        qualified = (
            f"{semantic.schema_name}.{semantic.fact_table}.{metric.column}"
        )
        return {
            "sum": f"SUM({qualified})",
            "avg": f"AVG({qualified})",
            "count": f"COUNT({qualified})",
            "count_distinct": f"COUNT(DISTINCT {qualified})",
        }[metric.aggregation]

    @staticmethod
    def _find_table(
        catalog: PostgresCatalog,
        schema_name: str,
        table_name: str,
    ) -> CatalogTable:
        for table in catalog.tables:
            if (
                table.schema_name == schema_name
                and table.table_name == table_name
            ):
                return table
        raise ValueError(
            f"configured fact table is not present in governed catalog: "
            f"{schema_name}.{table_name}"
        )

    @staticmethod
    def _validate_identifier(value: str) -> None:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError(f"unsafe SQL identifier: {value!r}")

    def _quote(self, value: str) -> str:
        self._validate_identifier(value)
        return self.engine.dialect.identifier_preparer.quote(value)


class PostgresDomainRuntime:
    """Canonical-domain adapter for an enterprise PostgreSQL source."""

    domain_id = "postgres-enterprise"

    def __init__(
        self,
        connector: PostgresEnterpriseConnector,
        semantic: PostgresSemanticConfig,
    ) -> None:
        self.connector = connector
        self.semantic_config = semantic
        self.catalog = connector.introspect()
        self.semantic_package = connector.build_semantic_package(
            semantic,
            catalog=self.catalog,
        )

    def capabilities(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "connector": "postgresql",
            "read_only": True,
            "catalog_hash": self.catalog.catalog_hash,
            "semantic_package": {
                "id": self.semantic_package.package.id,
                "version": self.semantic_package.package.version,
                "content_hash": self.semantic_package.content_hash,
            },
            "tables": [
                f"{table.schema_name}.{table.table_name}"
                for table in self.catalog.tables
            ],
        }

    def analyze(
        self,
        request: PostgresAnalysisRequest | dict[str, Any],
        *,
        on_event: DomainEventCallback | None = None,
    ) -> PostgresAnalysisResponse:
        resolved = (
            request
            if isinstance(request, PostgresAnalysisRequest)
            else PostgresAnalysisRequest.model_validate(request)
        )
        if on_event is not None:
            on_event(
                {
                    "event_type": "connector_analysis_started",
                    "domain_id": self.domain_id,
                }
            )
        response = self.connector.analyze(
            resolved,
            semantic=self.semantic_config,
            package=self.semantic_package,
            catalog=self.catalog,
        )
        if on_event is not None:
            on_event(
                {
                    "event_type": "connector_analysis_completed",
                    "domain_id": self.domain_id,
                    "task_id": response.task_id,
                    "evidence_id": response.evidence["evidence_id"],
                }
            )
        return response
