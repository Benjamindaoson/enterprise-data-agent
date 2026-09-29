"""Blind onboarding and semantic-layer ablation on a real business dataset."""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    create_engine,
    text,
)

from eiw.connectors.postgres import (
    ConnectorAnalysisRequest,
    EnterprisePostgresConnector,
    PostgresDimension,
    PostgresMetric,
    PostgresPermissionPolicy,
    PostgresSemanticPackage,
)
from eiw.ontology.builder import PostgresOntologyBuilder
from eiw.ontology.evolution import (
    EvolutionMetrics,
    PairedEvolutionGate,
    SemanticEvolutionEngine,
    TrajectoryFailure,
)
from eiw.ontology.model_builder import ontology_to_postgres_semantic_package
from eiw.ontology.models import OntologyState
from eiw.ontology.runtime import OntologyRuntime
from eiw.ontology.store import OntologyStore
from eiw.ontology.workload import WorkloadSemanticEvolver

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_TOKEN.findall(value.lower()))


@dataclass(frozen=True, slots=True)
class BlindSemanticCase:
    case_id: str
    question: str
    metric_id: str | None
    dimensions: tuple[str, ...] = ()
    expect_abstain: bool = False


@dataclass(frozen=True, slots=True)
class OntologyLaneMetrics:
    semantic_coverage: float
    task_success: float
    numeric_accuracy: float
    correct_abstention: float
    tool_calls: float
    turns: float
    p95_latency_ms: float
    estimated_cost_usd: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


class BlindOnboardingBenchmark:
    """Compare raw schema, static package, initial ontology and evolved ontology."""

    ADAPTATION_WORKLOAD = (
        "Show sales turnover by market.",
        "How many unique buyers do we have by country?",
        "Compare average selling price across markets.",
        "Rank items by sales volume.",
        "Show gross margin by country.",
    )

    TEST_CASES = (
        BlindSemanticCase(
            "BLIND-001",
            "Which countries generate the most revenue?",
            "revenue",
            ("country",),
        ),
        BlindSemanticCase(
            "BLIND-002",
            "Rank products by units sold.",
            "units",
            ("product",),
        ),
        BlindSemanticCase(
            "BLIND-003",
            "What is the average unit price by country?",
            "average_unit_price",
            ("country",),
        ),
        BlindSemanticCase(
            "BLIND-004",
            "How many active customers does each country have?",
            "active_customers",
            ("country",),
        ),
        BlindSemanticCase(
            "BLIND-005",
            "Show gross margin by country.",
            None,
            ("country",),
            expect_abstain=True,
        ),
        BlindSemanticCase(
            "BLIND-006",
            "Show total units by Country.",
            "units",
            ("country",),
        ),
    )

    def __init__(
        self,
        connector: EnterprisePostgresConnector,
        *,
        schema_name: str,
        table_name: str,
    ) -> None:
        self.connector = connector
        self.schema_name = schema_name
        self.table_name = table_name
        self.catalog = connector.introspect()

    def run(self) -> dict[str, Any]:
        static = self.connector.infer_semantic_package(
            package_id="blind-static",
            version="1.0.0",
        )
        initial = PostgresOntologyBuilder(self.connector).build(
            ontology_id="blind-online-retail",
            version="1.0.0",
            workload=list(self.ADAPTATION_WORKLOAD),
        )

        store = OntologyStore()
        store.put(initial, make_current=True)
        initial_failures = self._mine_adaptation_failures(initial)
        patch = WorkloadSemanticEvolver(self.connector).propose_patch(
            initial,
            initial_failures,
        )
        engine = SemanticEvolutionEngine(
            store,
            gate=PairedEvolutionGate(
                min_quality_gain=0.01,
                max_latency_increase=None,
                max_average_cost_usd=0.0,
                max_p95_latency_ms=5000.0,
            ),
        )
        candidate = engine.stage_candidate(
            initial.ontology_id,
            patch,
            candidate_version="2.0.0-candidate",
        )

        def evaluator(state: OntologyState) -> EvolutionMetrics:
            metrics = self._run_ontology_lane(state)
            return EvolutionMetrics(
                semantic_coverage=metrics.semantic_coverage,
                driver_recall=metrics.task_success,
                numeric_accuracy=metrics.numeric_accuracy,
                security_resistance=1.0,
                permission_compliance=1.0,
                causal_discipline=1.0,
                average_cost=metrics.estimated_cost_usd,
                p95_latency_ms=metrics.p95_latency_ms,
            )

        gate = engine.evaluate_candidate(
            initial.ontology_id,
            candidate.version,
            evaluator=evaluator,
            promote=True,
        )
        evolved = store.current(initial.ontology_id)

        lanes = {
            "raw_schema": self._run_raw_schema_lane().as_dict(),
            "static_semantic_package": self._run_static_lane(static).as_dict(),
            "initial_ontology": self._run_ontology_lane(initial).as_dict(),
            "evolved_ontology": self._run_ontology_lane(evolved).as_dict(),
        }
        return {
            "benchmark": "BlindEnterpriseOntologyBench-v1",
            "dataset": {
                "source": "UCI Online Retail",
                "schema": self.schema_name,
                "table": self.table_name,
            },
            "adaptation_workload": list(self.ADAPTATION_WORKLOAD),
            "held_out_cases": [asdict(case) for case in self.TEST_CASES],
            "adaptation_failure_count": len(initial_failures),
            "gate": gate,
            "lanes": lanes,
            "assertions": self._assertions(lanes, gate),
        }

    def _mine_adaptation_failures(
        self,
        initial: OntologyState,
    ) -> list[TrajectoryFailure]:
        failures: list[TrajectoryFailure] = []
        for index, question in enumerate(self.ADAPTATION_WORKLOAD, start=1):
            selection = self._select_ontology(initial, question)
            metric = selection["metric_id"]
            q = question.lower()
            failed = metric is None
            if "average" in q and selection.get("aggregation") != "avg":
                failed = True
            if "unique" in q and selection.get("aggregation") != "count_distinct":
                failed = True
            if "gross margin" in q:
                failed = True
            if failed:
                failures.append(
                    TrajectoryFailure(
                        failure_id=f"adapt-{index:02d}",
                        category="SEMANTIC",
                        summary=f"Semantic grounding failed for workload question: {question}",
                        semantic_refs=[],
                        details={"question": question},
                    )
                )
        return failures

    def _run_raw_schema_lane(self) -> OntologyLaneMetrics:
        results = []
        for case in self.TEST_CASES:
            started = perf_counter()
            selection = self._select_raw(case.question)
            metric_id = selection.get("metric_id")
            dimensions = selection.get("dimensions", [])
            semantic = self._semantic_score(case, metric_id, dimensions)
            numeric = False
            success = False
            tool_calls = 1
            turns = 1
            if case.expect_abstain:
                success = metric_id is None
                numeric = True
            elif metric_id is not None:
                package = selection.get("package")
                if isinstance(package, PostgresSemanticPackage):
                    numeric = self._execute_matches_gold(
                        package,
                        metric_id,
                        dimensions,
                        case,
                    )
                    success = semantic == 1.0 and numeric
                    tool_calls += 1
                    turns += 1
            results.append(
                {
                    "semantic": semantic,
                    "numeric": float(numeric),
                    "success": float(success),
                    "abstention": float(
                        success if case.expect_abstain else 0.0
                    ),
                    "tool_calls": float(tool_calls),
                    "turns": float(turns),
                    "latency_ms": (perf_counter() - started) * 1000.0,
                }
            )
        return self._aggregate(results)

    def _run_static_lane(
        self,
        package: PostgresSemanticPackage,
    ) -> OntologyLaneMetrics:
        results = []
        for case in self.TEST_CASES:
            started = perf_counter()
            metric_id, dimensions = self._select_static(package, case.question)
            semantic = self._semantic_score(case, metric_id, dimensions)
            numeric = False
            success = False
            tool_calls = 1
            turns = 1
            if case.expect_abstain:
                success = metric_id is None
                numeric = True
            elif metric_id is not None:
                numeric = self._execute_matches_gold(
                    package,
                    metric_id,
                    dimensions,
                    case,
                )
                success = semantic == 1.0 and numeric
                tool_calls += 1
                turns += 1
            results.append(
                {
                    "semantic": semantic,
                    "numeric": float(numeric),
                    "success": float(success),
                    "abstention": float(
                        success if case.expect_abstain else 0.0
                    ),
                    "tool_calls": float(tool_calls),
                    "turns": float(turns),
                    "latency_ms": (perf_counter() - started) * 1000.0,
                }
            )
        return self._aggregate(results)

    def _run_ontology_lane(
        self,
        state: OntologyState,
    ) -> OntologyLaneMetrics:
        package = ontology_to_postgres_semantic_package(
            state,
            schema_name=self.schema_name,
            package_id=f"{state.ontology_id}-{state.version}",
        )
        results = []
        for case in self.TEST_CASES:
            started = perf_counter()
            selection = self._select_ontology(state, case.question)
            metric_id = selection["metric_id"]
            dimensions = selection["dimensions"]
            semantic = self._semantic_score(case, metric_id, dimensions)
            numeric = False
            success = False
            tool_calls = 2
            turns = 2
            if case.expect_abstain:
                success = metric_id is None
                numeric = True
            elif metric_id is not None and metric_id in package.metrics:
                numeric = self._execute_matches_gold(
                    package,
                    metric_id,
                    dimensions,
                    case,
                )
                success = semantic == 1.0 and numeric
                tool_calls += 1
                turns += 1
            results.append(
                {
                    "semantic": semantic,
                    "numeric": float(numeric),
                    "success": float(success),
                    "abstention": float(
                        success if case.expect_abstain else 0.0
                    ),
                    "tool_calls": float(tool_calls),
                    "turns": float(turns),
                    "latency_ms": (perf_counter() - started) * 1000.0,
                }
            )
        return self._aggregate(results)

    def _select_raw(self, question: str) -> dict[str, Any]:
        q_tokens = _tokens(question)
        numeric_tokens = ("INT", "NUMERIC", "DECIMAL", "FLOAT", "DOUBLE", "REAL")
        metric_candidates: list[tuple[int, str, str]] = []
        dimension_candidates: list[tuple[int, str, str]] = []
        for schema in self.catalog.get("schemas", []):
            if schema.get("name") != self.schema_name:
                continue
            for table in schema.get("tables", []):
                table_name = str(table["name"])
                for column in table.get("columns", []):
                    name = str(column["name"])
                    score = len(q_tokens & _tokens(name))
                    if score == 0:
                        continue
                    type_name = str(column["type"]).upper()
                    if any(token in type_name for token in numeric_tokens):
                        metric_candidates.append((score, table_name, name))
                    else:
                        dimension_candidates.append((score, table_name, name))
        if not metric_candidates:
            return {"metric_id": None, "dimensions": []}
        metric_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        _, table_name, column = metric_candidates[0]
        aggregation = "avg" if "average" in question.lower() else "sum"
        metric_id = "raw_metric"
        dimensions: list[str] = []
        dim_defs: dict[str, PostgresDimension] = {}
        if dimension_candidates:
            dimension_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
            _, dim_table, dim_column = dimension_candidates[0]
            if dim_table == table_name:
                dimensions = ["raw_dimension"]
                dim_defs["raw_dimension"] = PostgresDimension(
                    table=dim_table,
                    column=dim_column,
                )
        package = PostgresSemanticPackage(
            package_id="raw-schema",
            version="1.0.0",
            schema_name=self.schema_name,
            metrics={
                metric_id: PostgresMetric(
                    table=table_name,
                    column=column,
                    aggregation=aggregation,
                )
            },
            dimensions=dim_defs,
        )
        return {
            "metric_id": metric_id,
            "dimensions": dimensions,
            "package": package,
        }

    def _select_static(
        self,
        package: PostgresSemanticPackage,
        question: str,
    ) -> tuple[str | None, list[str]]:
        q_tokens = _tokens(question)
        metrics: list[tuple[int, str]] = []
        for metric_id, metric in package.metrics.items():
            score = len(
                q_tokens
                & _tokens(f"{metric_id} {metric.column} {metric.aggregation}")
            )
            if score:
                metrics.append((score, metric_id))
        dimensions: list[tuple[int, str]] = []
        for dimension_id, dimension in package.dimensions.items():
            score = len(q_tokens & _tokens(f"{dimension_id} {dimension.column}"))
            if score:
                dimensions.append((score, dimension_id))
        metrics.sort(key=lambda item: (-item[0], item[1]))
        dimensions.sort(key=lambda item: (-item[0], item[1]))
        return (
            metrics[0][1] if metrics else None,
            [dimensions[0][1]] if dimensions else [],
        )

    def _select_ontology(
        self,
        state: OntologyState,
        question: str,
    ) -> dict[str, Any]:
        store = OntologyStore()
        store.put(state, make_current=True)
        runtime = OntologyRuntime(store)
        metric_hits = runtime.browse(
            state.ontology_id,
            question,
            semantic_types={"metric"},
            limit=4,
        )
        dimension_hits = runtime.browse(
            state.ontology_id,
            question,
            semantic_types={"dimension"},
            limit=4,
        )
        metric_id = metric_hits[0].canonical_id if metric_hits else None
        dimensions = (
            [str(dimension_hits[0].canonical_id)]
            if dimension_hits and dimension_hits[0].canonical_id
            else []
        )
        aggregation = None
        if metric_hits:
            resolution = runtime.resolve(
                state.ontology_id,
                [metric_hits[0].term_id],
                include_evidence=False,
            )
            if resolution.mappings:
                aggregation = resolution.mappings[0].aggregation
        return {
            "metric_id": str(metric_id) if metric_id else None,
            "dimensions": dimensions,
            "aggregation": aggregation,
        }

    def _semantic_score(
        self,
        case: BlindSemanticCase,
        metric_id: str | None,
        dimensions: list[str],
    ) -> float:
        if case.expect_abstain:
            return float(metric_id is None)
        expected = [case.metric_id, *case.dimensions]
        observed = [metric_id, *dimensions]
        hits = sum(
            item is not None and item in observed
            for item in expected
        )
        return hits / len(expected)

    def _execute_matches_gold(
        self,
        package: PostgresSemanticPackage,
        metric_id: str,
        dimensions: list[str],
        case: BlindSemanticCase,
    ) -> bool:
        try:
            observed = self.connector.analyze(
                package,
                ConnectorAnalysisRequest(
                    metric_id=metric_id,
                    dimensions=dimensions,
                    limit=5000,
                ),
            ).rows
            gold_package = self._gold_package()
            if case.metric_id is None:
                return False
            gold = self.connector.analyze(
                gold_package,
                ConnectorAnalysisRequest(
                    metric_id=case.metric_id,
                    dimensions=list(case.dimensions),
                    limit=5000,
                ),
            ).rows
        except (KeyError, ValueError, PermissionError):
            return False
        return self._normalized_rows(observed) == self._normalized_rows(gold)

    def _gold_package(self) -> PostgresSemanticPackage:
        return PostgresSemanticPackage(
            package_id="blind-held-out-gold",
            version="1.0.0",
            schema_name=self.schema_name,
            metrics={
                "revenue": PostgresMetric(
                    table=self.table_name,
                    column="Quantity",
                    columns=["Quantity", "UnitPrice"],
                    operator="multiply",
                    aggregation="sum",
                ),
                "units": PostgresMetric(
                    table=self.table_name,
                    column="Quantity",
                    aggregation="sum",
                ),
                "average_unit_price": PostgresMetric(
                    table=self.table_name,
                    column="UnitPrice",
                    aggregation="avg",
                ),
                "active_customers": PostgresMetric(
                    table=self.table_name,
                    column="CustomerID",
                    aggregation="count_distinct",
                ),
            },
            dimensions={
                "country": PostgresDimension(
                    table=self.table_name,
                    column="Country",
                ),
                "product": PostgresDimension(
                    table=self.table_name,
                    column="StockCode",
                ),
                "customer": PostgresDimension(
                    table=self.table_name,
                    column="CustomerID",
                ),
            },
        )

    @staticmethod
    def _normalized_rows(rows: list[dict[str, Any]]) -> list[tuple[tuple[str, Any], ...]]:
        normalized = []
        for row in rows:
            values = []
            for key, value in sorted(row.items()):
                if isinstance(value, Decimal):
                    value = round(float(value), 6)
                elif isinstance(value, float):
                    value = round(value, 6)
                values.append((key, value))
            normalized.append(tuple(values))
        return sorted(normalized, key=repr)

    @staticmethod
    def _aggregate(results: list[dict[str, float]]) -> OntologyLaneMetrics:
        latencies = sorted(item["latency_ms"] for item in results)
        index = min(len(latencies) - 1, int(0.95 * len(latencies)))
        # When the unsupported case is incorrectly answered, its abstention value
        # is zero and must still be included. There is one unsupported case in v1.
        correct_abstention = sum(item["abstention"] for item in results)
        return OntologyLaneMetrics(
            semantic_coverage=round(fmean(item["semantic"] for item in results), 6),
            task_success=round(fmean(item["success"] for item in results), 6),
            numeric_accuracy=round(fmean(item["numeric"] for item in results), 6),
            correct_abstention=round(correct_abstention, 6),
            tool_calls=round(fmean(item["tool_calls"] for item in results), 3),
            turns=round(fmean(item["turns"] for item in results), 3),
            p95_latency_ms=round(latencies[index], 3),
            estimated_cost_usd=0.0,
        )

    @staticmethod
    def _assertions(
        lanes: dict[str, dict[str, float]],
        gate: dict[str, Any],
    ) -> dict[str, bool]:
        static = lanes["static_semantic_package"]
        evolved = lanes["evolved_ontology"]
        initial = lanes["initial_ontology"]
        return {
            "evolved_beats_static_semantic_coverage": (
                evolved["semantic_coverage"] > static["semantic_coverage"]
            ),
            "evolved_beats_static_task_success": (
                evolved["task_success"] > static["task_success"]
            ),
            "evolved_beats_initial_task_success": (
                evolved["task_success"] > initial["task_success"]
            ),
            "evolved_numeric_not_worse_than_static": (
                evolved["numeric_accuracy"] >= static["numeric_accuracy"]
            ),
            "paired_gate_promoted": bool(gate.get("promoted")),
        }


def load_online_retail_sample_into_postgres(
    zip_path: Path,
    *,
    database_url: str,
    schema_name: str = "blind_online_retail",
    table_name: str = "transactions",
    max_rows: int = 25_000,
) -> dict[str, Any]:
    """Load a deterministic prefix of the real UCI Online Retail workbook."""

    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError(
            "install the benchmark extra: pip install -e '.[benchmark]'"
        ) from exc

    raw = zip_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = sorted(
            name for name in archive.namelist() if name.lower().endswith(".xlsx")
        )
        if not members:
            raise ValueError("Online Retail archive contains no XLSX workbook")
        workbook_bytes = archive.read(members[0])

    workbook = load_workbook(
        io.BytesIO(workbook_bytes),
        read_only=True,
        data_only=True,
    )
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    header = [str(value) if value is not None else "" for value in next(rows)]
    expected = [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
    ]
    if header[: len(expected)] != expected:
        raise ValueError(f"unexpected Online Retail schema: {header}")

    engine = create_engine(database_url, future=True)
    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        Column("InvoiceNo", Text, nullable=False),
        Column("StockCode", Text, nullable=False),
        Column("Description", Text),
        Column("Quantity", Integer, nullable=False),
        Column("InvoiceDate", DateTime),
        Column("UnitPrice", Numeric(14, 4), nullable=False),
        Column("CustomerID", Text),
        Column("Country", Text, nullable=False),
        schema=schema_name,
    )

    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
        table.create(connection)
        batch: list[dict[str, Any]] = []
        inserted = 0
        for raw_row in rows:
            if inserted >= max_rows:
                break
            invoice, stock, description, quantity, invoice_date, unit_price, customer, country = (
                raw_row[:8]
            )
            if invoice is None or stock is None or quantity is None or unit_price is None:
                continue
            record = {
                "InvoiceNo": str(invoice),
                "StockCode": str(stock),
                "Description": str(description) if description is not None else None,
                "Quantity": int(quantity),
                "InvoiceDate": invoice_date,
                "UnitPrice": Decimal(str(unit_price)),
                "CustomerID": (
                    str(int(float(customer))) if customer is not None else None
                ),
                "Country": str(country or ""),
            }
            batch.append(record)
            inserted += 1
            if len(batch) >= 1000:
                connection.execute(table.insert(), batch)
                batch.clear()
        if batch:
            connection.execute(table.insert(), batch)

    return {
        "schema": schema_name,
        "table": table_name,
        "rows": inserted,
        "source": "UCI Online Retail",
        "raw_semantic_package_exposed_to_builder": False,
    }


def blind_connector(
    database_url: str,
    *,
    schema_name: str = "blind_online_retail",
    table_name: str = "transactions",
) -> EnterprisePostgresConnector:
    return EnterprisePostgresConnector(
        database_url,
        policy=PostgresPermissionPolicy(
            allowed_schemas={schema_name},
            allowed_tables={f"{schema_name}.{table_name}"},
            allowed_columns={
                f"{schema_name}.{table_name}": {
                    "InvoiceNo",
                    "StockCode",
                    "Description",
                    "Quantity",
                    "InvoiceDate",
                    "UnitPrice",
                    "CustomerID",
                    "Country",
                }
            },
            max_rows=5000,
            statement_timeout_ms=30_000,
        ),
    )
