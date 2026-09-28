from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from eiw.connectors.postgres import (
    EnterprisePostgresConnector,
    PostgresPermissionPolicy,
)
from eiw.ontology.builder import PostgresOntologyBuilder
from eiw.ontology.runtime import OntologyRuntime
from eiw.ontology.store import OntologyStore


@pytest.mark.integration
def test_postgres_builder_constructs_evidence_grounded_ontology_without_raw_values() -> None:
    database_url = os.getenv("EIW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("EIW_TEST_DATABASE_URL is required for PostgreSQL integration")

    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS ontology_demo CASCADE"))
        connection.execute(text("CREATE SCHEMA ontology_demo"))
        connection.execute(
            text(
                """
                CREATE TABLE ontology_demo.sales_orders (
                    order_id INTEGER PRIMARY KEY,
                    region TEXT NOT NULL,
                    category TEXT NOT NULL,
                    net_revenue NUMERIC(12, 2) NOT NULL,
                    units INTEGER NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO ontology_demo.sales_orders
                    (order_id, region, category, net_revenue, units)
                VALUES
                    (1, 'East', 'A', 100.00, 2),
                    (2, 'East', 'B', 75.00, 1),
                    (3, 'West', 'A', 50.00, 1)
                """
            )
        )

    connector = EnterprisePostgresConnector(
        database_url,
        policy=PostgresPermissionPolicy(
            allowed_schemas={"ontology_demo"},
            allowed_tables={"ontology_demo.sales_orders"},
            allowed_columns={
                "ontology_demo.sales_orders": {
                    "order_id",
                    "region",
                    "category",
                    "net_revenue",
                    "units",
                }
            },
        ),
    )
    state = PostgresOntologyBuilder(connector).build(
        ontology_id="sales-demo",
        workload=[
            "Analyze revenue by region",
            "Compare category units and revenue",
        ],
    )

    assert state.metadata["builder"] == "PostgresOntologyBuilder-v1"
    assert state.metadata["human_review_required"] is True
    assert state.metadata["raw_sample_values_stored"] is False
    assert state.terms
    assert state.mappings
    assert state.evidence
    assert any(
        term.canonical_id and "net_revenue" in term.canonical_id
        for term in state.terms.values()
    )
    assert all(
        item.payload.get("raw_values_returned") is False
        for item in state.evidence.values()
        if item.evidence_type == "postgres_column_probe"
    )
    assert all(
        "sample" not in key.lower()
        for item in state.evidence.values()
        for key in item.payload
    )

    store = OntologyStore()
    store.put(state, make_current=True)
    runtime = OntologyRuntime(store)
    hits = runtime.browse("sales-demo", "revenue by region", limit=10)
    assert any(
        hit.canonical_id and "net_revenue" in hit.canonical_id
        for hit in hits
    )
    assert any(
        hit.canonical_id and "region" in hit.canonical_id
        for hit in hits
    )
