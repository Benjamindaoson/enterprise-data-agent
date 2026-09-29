from __future__ import annotations

from typing import Any

import pytest

from eiw.connectors.postgres import (
    PostgresDimension,
    PostgresMetric,
    PostgresSemanticPackage,
)
from eiw.ontology.model_builder import (
    ModelDrivenPostgresOntologyBuilder,
    ModelSemanticConcept,
    ModelSemanticMapping,
    ModelSemanticPlan,
    OpenAIResponsesSemanticBuilderModel,
    SemanticModelUsage,
    ontology_to_postgres_semantic_package,
)


class FakeConnector:
    def introspect(self) -> dict[str, Any]:
        return {
            "dialect": "postgresql",
            "schemas": [
                {
                    "name": "blind",
                    "tables": [
                        {
                            "name": "transactions",
                            "columns": [
                                {"name": "Quantity", "type": "INTEGER", "nullable": False},
                                {"name": "UnitPrice", "type": "NUMERIC", "nullable": False},
                                {"name": "CustomerID", "type": "TEXT", "nullable": True},
                                {"name": "Country", "type": "TEXT", "nullable": False},
                            ],
                            "primary_key": [],
                            "foreign_keys": [],
                        }
                    ],
                }
            ],
        }

    def infer_semantic_package(
        self,
        *,
        package_id: str = "postgres_inferred",
        version: str = "1.0.0",
    ) -> PostgresSemanticPackage:
        return PostgresSemanticPackage(
            package_id=package_id,
            version=version,
            schema_name="blind",
            metrics={
                "transactions__Quantity__sum": PostgresMetric(
                    table="transactions",
                    column="Quantity",
                    aggregation="sum",
                ),
                "transactions__UnitPrice__sum": PostgresMetric(
                    table="transactions",
                    column="UnitPrice",
                    aggregation="sum",
                ),
            },
            dimensions={
                "transactions__CustomerID": PostgresDimension(
                    table="transactions",
                    column="CustomerID",
                ),
                "transactions__Country": PostgresDimension(
                    table="transactions",
                    column="Country",
                ),
            },
        )

    def probe_column(
        self,
        schema: str,
        table_name: str,
        column_name: str,
    ) -> dict[str, Any]:
        return {
            "schema": schema,
            "table": table_name,
            "column": column_name,
            "type": "TEXT" if column_name in {"CustomerID", "Country"} else "NUMERIC",
            "nullable": column_name == "CustomerID",
            "row_count": 100,
            "non_null_count": 95,
            "null_count": 5,
            "distinct_count": 20,
            "query_sha256": "a" * 64,
            "raw_values_returned": False,
        }


class FakeModel:
    def __init__(self, *, hallucinate: bool = False) -> None:
        self.hallucinate = hallucinate

    def propose(
        self,
        payload: dict[str, Any],
    ) -> tuple[ModelSemanticPlan, SemanticModelUsage]:
        assert payload["workload"]
        revenue_columns = ["Quantity", "Cost"] if self.hallucinate else ["Quantity", "UnitPrice"]
        return (
            ModelSemanticPlan(
                concepts=[
                    ModelSemanticConcept(
                        concept_id="revenue",
                        label="Revenue",
                        semantic_type="metric",
                        aliases=["sales", "turnover"],
                        mappings=[
                            ModelSemanticMapping(
                                table="transactions",
                                columns=revenue_columns,
                                aggregation="sum",
                                operator="multiply",
                            )
                        ],
                    ),
                    ModelSemanticConcept(
                        concept_id="country",
                        label="Country",
                        semantic_type="dimension",
                        mappings=[
                            ModelSemanticMapping(
                                table="transactions",
                                columns=["Country"],
                            )
                        ],
                    ),
                ],
                unsupported_business_concepts=["gross_margin"],
            ),
            SemanticModelUsage(
                provider="fake",
                model="semantic-test",
                latency_ms=1.0,
            ),
        )


def test_model_builder_creates_executable_derived_business_metric() -> None:
    builder = ModelDrivenPostgresOntologyBuilder(FakeConnector(), FakeModel())  # type: ignore[arg-type]
    state, usage = builder.build(
        ontology_id="blind",
        version="model-v1",
        workload=["Show revenue by country", "Show gross margin"],
    )

    package = ontology_to_postgres_semantic_package(
        state,
        schema_name="blind",
    )
    revenue = package.metrics["revenue"]
    assert revenue.operator == "multiply"
    assert revenue.referenced_columns() == ["Quantity", "UnitPrice"]
    assert revenue.aggregation == "sum"
    assert package.dimensions["country"].column == "Country"
    assert "constraint:unsupported:gross_margin" in state.constraints
    assert usage.provider == "fake"


def test_model_builder_rejects_hallucinated_physical_column() -> None:
    builder = ModelDrivenPostgresOntologyBuilder(  # type: ignore[arg-type]
        FakeConnector(),
        FakeModel(hallucinate=True),
    )
    with pytest.raises(ValueError, match="unknown column"):
        builder.build(
            ontology_id="blind",
            workload=["Show revenue by country"],
        )


def test_openai_responses_builder_parses_typed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "output_text": (
                    '{"concepts":[{"concept_id":"revenue","label":"Revenue",'
                    '"semantic_type":"metric","aliases":["sales"],'
                    '"mappings":[{"table":"transactions",'
                    '"columns":["Quantity","UnitPrice"],"aggregation":"sum",'
                    '"operator":"multiply"}],"constraints":[]}],'
                    '"unsupported_business_concepts":[],"rationale":"grounded"}'
                ),
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)
    model = OpenAIResponsesSemanticBuilderModel(
        api_key="test-key",
        model="gpt-6-luna",
    )
    plan, usage = model.propose(
        {
            "catalog": {"schemas": []},
            "workload": ["revenue"],
            "safe_probes": [],
            "seed_terms": [],
        }
    )

    assert plan.concepts[0].concept_id == "revenue"
    assert usage.model == "gpt-6-luna"
    assert usage.input_tokens == 100
    assert captured["json"]["store"] is False
    assert captured["json"]["model"] == "gpt-6-luna"
