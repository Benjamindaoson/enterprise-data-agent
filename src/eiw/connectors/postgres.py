"""Governed read-only PostgreSQL enterprise analytics connector."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import MetaData, Table, case, create_engine, func, inspect, select
from sqlalchemy.engine import Engine

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PostgresPermissionPolicy(BaseModel):
    allowed_schemas: set[str] = Field(default_factory=set)
    allowed_tables: set[str] = Field(default_factory=set)
    allowed_columns: dict[str, set[str]] = Field(default_factory=dict)
    max_rows: int = Field(default=200, ge=1, le=5000)
    statement_timeout_ms: int = Field(default=5000, ge=100, le=120000)

    def allows_table(self, schema: str, table: str) -> bool:
        qualified = f"{schema}.{table}"
        return schema in self.allowed_schemas and (
            not self.allowed_tables or qualified in self.allowed_tables
        )

    def allows_column(self, schema: str, table: str, column: str) -> bool:
        qualified = f"{schema}.{table}"
        configured = self.allowed_columns.get(qualified)
        return configured is None or not configured or column in configured


class PostgresMetric(BaseModel):
    table: str
    column: str
    aggregation: Literal[
        "sum",
        "avg",
        "count",
        "min",
        "max",
        "count_distinct",
        "rate_equals",
    ]
    columns: list[str] = Field(default_factory=list)
    predicate_value: str | int | float | bool | None = None
    operator: Literal["column", "multiply", "add", "subtract", "divide"] = "column"

    @model_validator(mode="after")
    def expression_contract_is_bounded(self) -> PostgresMetric:
        refs = self.referenced_columns()
        if self.operator == "column":
            if len(refs) != 1:
                raise ValueError("column metric must reference exactly one column")
        elif len(refs) != 2:
            raise ValueError(f"{self.operator} metric must reference exactly two columns")
        if self.aggregation == "rate_equals":
            if self.operator != "column":
                raise ValueError("rate_equals requires a single-column metric")
            if self.predicate_value is None:
                raise ValueError("rate_equals requires predicate_value")
        return self

    def referenced_columns(self) -> list[str]:
        return list(self.columns) if self.columns else [self.column]


class PostgresDimension(BaseModel):
    table: str
    column: str


class PostgresSemanticPackage(BaseModel):
    package_id: str
    version: str
    schema_name: str
    metrics: dict[str, PostgresMetric] = Field(default_factory=dict)
    dimensions: dict[str, PostgresDimension] = Field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class ConnectorAnalysisRequest(BaseModel):
    metric_id: str
    dimensions: list[str] = Field(default_factory=list)
    filters: dict[str, str | int | float] = Field(default_factory=dict)
    limit: int = Field(default=50, ge=1, le=5000)


class ConnectorEvidence(BaseModel):
    evidence_id: str
    source: str
    semantic_package_id: str
    semantic_version: str
    semantic_hash: str
    query_sha256: str
    query_template: str
    parameters: dict[str, Any]
    row_count: int
    captured_at: datetime


class ConnectorReport(BaseModel):
    title: str
    summary: list[str]
    rows: list[dict[str, Any]]
    evidence: ConnectorEvidence
    limitations: list[str] = Field(default_factory=list)


class ConnectorAnalysisResponse(BaseModel):
    metric_id: str
    dimensions: list[str]
    rows: list[dict[str, Any]]
    evidence: ConnectorEvidence
    report: ConnectorReport


class EnterprisePostgresConnector:
    """Read-only PostgreSQL connector with introspection and semantic governance."""

    def __init__(
        self,
        database_url: str,
        *,
        policy: PostgresPermissionPolicy,
    ) -> None:
        if not policy.allowed_schemas:
            raise ValueError("at least one allowed PostgreSQL schema is required")
        self.engine: Engine = create_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
        )
        self.policy = policy

    def ping(self) -> bool:
        with self.engine.connect() as connection:
            return bool(connection.exec_driver_sql("SELECT 1").scalar_one() == 1)

    def introspect(self) -> dict[str, Any]:
        inspector = inspect(self.engine)
        schemas: list[dict[str, Any]] = []
        for schema in sorted(self.policy.allowed_schemas):
            if schema not in inspector.get_schema_names():
                continue
            tables: list[dict[str, Any]] = []
            for table in sorted(inspector.get_table_names(schema=schema)):
                if not self.policy.allows_table(schema, table):
                    continue
                columns = [
                    {
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": bool(column.get("nullable", True)),
                    }
                    for column in inspector.get_columns(table, schema=schema)
                    if self.policy.allows_column(schema, table, str(column["name"]))
                ]
                tables.append(
                    {
                        "name": table,
                        "columns": columns,
                        "primary_key": inspector.get_pk_constraint(
                            table,
                            schema=schema,
                        ).get("constrained_columns", []),
                        "foreign_keys": inspector.get_foreign_keys(
                            table,
                            schema=schema,
                        ),
                    }
                )
            schemas.append({"name": schema, "tables": tables})
        return {"dialect": self.engine.dialect.name, "schemas": schemas}

    def infer_semantic_package(
        self,
        *,
        package_id: str = "postgres_inferred",
        version: str = "1.0.0",
    ) -> PostgresSemanticPackage:
        catalog = self.introspect()
        metrics: dict[str, PostgresMetric] = {}
        dimensions: dict[str, PostgresDimension] = {}
        chosen_schema = sorted(self.policy.allowed_schemas)[0]
        numeric_tokens = ("INT", "NUMERIC", "DECIMAL", "FLOAT", "DOUBLE", "REAL")

        for schema in catalog["schemas"]:
            if schema["name"] != chosen_schema:
                continue
            for table in schema["tables"]:
                table_name = str(table["name"])
                for column in table["columns"]:
                    column_name = str(column["name"])
                    type_name = str(column["type"]).upper()
                    identifier = f"{table_name}__{column_name}"
                    if any(token in type_name for token in numeric_tokens):
                        metrics[f"{identifier}__sum"] = PostgresMetric(
                            table=table_name,
                            column=column_name,
                            aggregation="sum",
                        )
                    else:
                        dimensions[identifier] = PostgresDimension(
                            table=table_name,
                            column=column_name,
                        )

        return PostgresSemanticPackage(
            package_id=package_id,
            version=version,
            schema_name=chosen_schema,
            metrics=metrics,
            dimensions=dimensions,
        )

    def validate_semantic_package(self, package: PostgresSemanticPackage) -> None:
        if package.schema_name not in self.policy.allowed_schemas:
            raise PermissionError(f"schema not allowed: {package.schema_name}")

        catalog = self.introspect()
        allowed_catalog: dict[str, set[str]] = {}
        for schema in catalog["schemas"]:
            if schema["name"] != package.schema_name:
                continue
            for table in schema["tables"]:
                allowed_catalog[str(table["name"])] = {
                    str(column["name"]) for column in table["columns"]
                }

        for metric_id, metric in package.metrics.items():
            self._validate_identifier(metric_id)
            for column in metric.referenced_columns():
                self._validate_catalog_ref(
                    package.schema_name,
                    metric.table,
                    column,
                    allowed_catalog,
                )
        for dimension_id, dimension in package.dimensions.items():
            self._validate_identifier(dimension_id)
            self._validate_catalog_ref(
                package.schema_name,
                dimension.table,
                dimension.column,
                allowed_catalog,
            )

    def analyze(
        self,
        package: PostgresSemanticPackage,
        request: ConnectorAnalysisRequest,
    ) -> ConnectorAnalysisResponse:
        self.validate_semantic_package(package)
        try:
            metric = package.metrics[request.metric_id]
        except KeyError as exc:
            raise KeyError(f"unknown metric: {request.metric_id}") from exc

        dimensions = []
        for dimension_id in request.dimensions:
            try:
                dimensions.append((dimension_id, package.dimensions[dimension_id]))
            except KeyError as exc:
                raise KeyError(f"unknown dimension: {dimension_id}") from exc

        tables = {metric.table, *(dimension.table for _, dimension in dimensions)}
        if len(tables) != 1:
            raise ValueError(
                "PostgreSQL connector v1 requires metric and dimensions from one table"
            )

        metadata = MetaData()
        table = Table(
            metric.table,
            metadata,
            schema=package.schema_name,
            autoload_with=self.engine,
        )
        metric_expression = self._metric_expression(table, metric)
        if metric.aggregation == "rate_equals":
            aggregate = func.avg(
                case(
                    (metric_expression == metric.predicate_value, 1.0),
                    else_=0.0,
                )
            ).label(request.metric_id)
        else:
            aggregate_builders = {
                "sum": func.sum,
                "avg": func.avg,
                "count": func.count,
                "min": func.min,
                "max": func.max,
                "count_distinct": lambda value: func.count(func.distinct(value)),
            }
            aggregate = aggregate_builders[metric.aggregation](metric_expression).label(
                request.metric_id
            )

        dimension_columns = [
            table.c[dimension.column].label(dimension_id)
            for dimension_id, dimension in dimensions
        ]
        statement = select(*dimension_columns, aggregate).select_from(table)

        parameters: dict[str, Any] = {}
        if metric.aggregation == "rate_equals":
            parameters[f"metric:{request.metric_id}:predicate"] = metric.predicate_value
        for dimension_id, value in request.filters.items():
            if dimension_id not in package.dimensions:
                raise KeyError(f"filter must reference a governed dimension: {dimension_id}")
            dimension = package.dimensions[dimension_id]
            if dimension.table != metric.table:
                raise ValueError("cross-table filters are not supported")
            statement = statement.where(table.c[dimension.column] == value)
            parameters[dimension_id] = value

        if dimension_columns:
            statement = statement.group_by(*dimension_columns)
        statement = statement.order_by(aggregate.desc()).limit(
            min(request.limit, self.policy.max_rows)
        )

        compiled = statement.compile(
            dialect=self.engine.dialect,
            compile_kwargs={"literal_binds": False},
        )
        query_template = str(compiled)
        query_sha = hashlib.sha256(query_template.encode("utf-8")).hexdigest()

        with self.engine.begin() as connection:
            if self.engine.dialect.name == "postgresql":
                connection.exec_driver_sql("SET LOCAL TRANSACTION READ ONLY")
                connection.exec_driver_sql(
                    f"SET LOCAL statement_timeout = {self.policy.statement_timeout_ms}"
                )
            rows = [
                dict(row)
                for row in connection.execute(statement).mappings().all()
            ]

        evidence = ConnectorEvidence(
            evidence_id=f"pg-{query_sha[:16]}",
            source=f"postgresql://{package.schema_name}.{metric.table}",
            semantic_package_id=package.package_id,
            semantic_version=package.version,
            semantic_hash=package.content_hash,
            query_sha256=query_sha,
            query_template=query_template,
            parameters=parameters,
            row_count=len(rows),
            captured_at=datetime.now(UTC),
        )
        summary = [
            (
                f"Computed governed metric '{request.metric_id}'"
                + (
                    " by " + ", ".join(request.dimensions)
                    if request.dimensions
                    else ""
                )
                + f" across {len(rows)} result rows."
            )
        ]
        if rows:
            summary.append(f"Top result: {rows[0]}")
        report = ConnectorReport(
            title=f"PostgreSQL analysis · {request.metric_id}",
            summary=summary,
            rows=rows,
            evidence=evidence,
            limitations=[
                "Connector execution is read-only and limited to the allowlisted catalog.",
                "The connector reports observed aggregates; it does not infer causality.",
            ],
        )
        return ConnectorAnalysisResponse(
            metric_id=request.metric_id,
            dimensions=request.dimensions,
            rows=rows,
            evidence=evidence,
            report=report,
        )

    def probe_column(
        self,
        schema: str,
        table_name: str,
        column_name: str,
    ) -> dict[str, Any]:
        """Profile one allowlisted column without returning raw sample values."""

        self._validate_identifier(table_name)
        self._validate_identifier(column_name)
        catalog = self.introspect()
        allowed_catalog: dict[str, set[str]] = {}
        type_names: dict[tuple[str, str], str] = {}
        nullable: dict[tuple[str, str], bool] = {}
        for schema_item in catalog["schemas"]:
            if schema_item["name"] != schema:
                continue
            for table in schema_item["tables"]:
                name = str(table["name"])
                allowed_catalog[name] = {
                    str(column["name"]) for column in table["columns"]
                }
                for column in table["columns"]:
                    key = (name, str(column["name"]))
                    type_names[key] = str(column["type"])
                    nullable[key] = bool(column["nullable"])
        self._validate_catalog_ref(
            schema,
            table_name,
            column_name,
            allowed_catalog,
        )

        metadata = MetaData()
        table = Table(
            table_name,
            metadata,
            schema=schema,
            autoload_with=self.engine,
        )
        column = table.c[column_name]
        statement = select(
            func.count().label("row_count"),
            func.count(column).label("non_null_count"),
            func.count(func.distinct(column)).label("distinct_count"),
        ).select_from(table)
        compiled = statement.compile(
            dialect=self.engine.dialect,
            compile_kwargs={"literal_binds": False},
        )
        query_template = str(compiled)
        query_sha = hashlib.sha256(query_template.encode("utf-8")).hexdigest()

        with self.engine.begin() as connection:
            if self.engine.dialect.name == "postgresql":
                connection.exec_driver_sql("SET LOCAL TRANSACTION READ ONLY")
                connection.exec_driver_sql(
                    f"SET LOCAL statement_timeout = {self.policy.statement_timeout_ms}"
                )
            row = connection.execute(statement).mappings().one()

        row_count = int(row["row_count"] or 0)
        non_null_count = int(row["non_null_count"] or 0)
        return {
            "schema": schema,
            "table": table_name,
            "column": column_name,
            "type": type_names.get((table_name, column_name), str(column.type)),
            "nullable": nullable.get((table_name, column_name), True),
            "row_count": row_count,
            "non_null_count": non_null_count,
            "null_count": max(0, row_count - non_null_count),
            "distinct_count": int(row["distinct_count"] or 0),
            "query_sha256": query_sha,
            "raw_values_returned": False,
        }

    @staticmethod
    def _metric_expression(table: Table, metric: PostgresMetric) -> Any:
        columns = [table.c[name] for name in metric.referenced_columns()]
        if metric.operator == "column":
            return columns[0]
        left, right = columns
        if metric.operator == "multiply":
            return left * right
        if metric.operator == "add":
            return left + right
        if metric.operator == "subtract":
            return left - right
        if metric.operator == "divide":
            return left / func.nullif(right, 0)
        raise ValueError(f"unsupported metric operator: {metric.operator}")

    def _validate_catalog_ref(
        self,
        schema: str,
        table: str,
        column: str,
        catalog: dict[str, set[str]],
    ) -> None:
        self._validate_identifier(table)
        self._validate_identifier(column)
        if not self.policy.allows_table(schema, table):
            raise PermissionError(f"table not allowed: {schema}.{table}")
        if not self.policy.allows_column(schema, table, column):
            raise PermissionError(f"column not allowed: {schema}.{table}.{column}")
        if table not in catalog or column not in catalog[table]:
            raise ValueError(f"semantic reference not found: {schema}.{table}.{column}")

    @staticmethod
    def _validate_identifier(value: str) -> None:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError(f"invalid identifier: {value}")
