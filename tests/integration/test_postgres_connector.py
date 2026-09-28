from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from eiw.connectors.postgres import (
    ConnectorAnalysisRequest,
    EnterprisePostgresConnector,
    PostgresDimension,
    PostgresMetric,
    PostgresPermissionPolicy,
    PostgresSemanticPackage,
)


@pytest.mark.integration
def test_postgres_connector_full_enterprise_flow() -> None:
    database_url = os.getenv("EIW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("EIW_TEST_DATABASE_URL is required for PostgreSQL integration")
    engine = create_engine(database_url, future=True)

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS connector_demo CASCADE"))
        connection.execute(text("CREATE SCHEMA connector_demo"))
        connection.execute(
            text(
                """
                CREATE TABLE connector_demo.sales_orders (
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
                INSERT INTO connector_demo.sales_orders
                    (order_id, region, category, net_revenue, units)
                VALUES
                    (1, 'East', 'A', 100.00, 2),
                    (2, 'East', 'B', 75.00, 1),
                    (3, 'West', 'A', 50.00, 1)
                """
            )
        )

    policy = PostgresPermissionPolicy(
        allowed_schemas={"connector_demo"},
        allowed_tables={"connector_demo.sales_orders"},
        allowed_columns={
            "connector_demo.sales_orders": {
                "order_id",
                "region",
                "category",
                "net_revenue",
                "units",
            }
        },
        max_rows=50,
    )
    connector = EnterprisePostgresConnector(database_url, policy=policy)

    assert connector.ping() is True
    catalog = connector.introspect()
    assert catalog["schemas"][0]["name"] == "connector_demo"
    assert catalog["schemas"][0]["tables"][0]["name"] == "sales_orders"

    inferred = connector.infer_semantic_package(package_id="inferred-demo")
    assert any(key.endswith("net_revenue__sum") for key in inferred.metrics)

    semantic = PostgresSemanticPackage(
        package_id="sales-orders",
        version="1.0.0",
        schema_name="connector_demo",
        metrics={
            "revenue": PostgresMetric(
                table="sales_orders",
                column="net_revenue",
                aggregation="sum",
            )
        },
        dimensions={
            "region": PostgresDimension(
                table="sales_orders",
                column="region",
            )
        },
    )
    connector.validate_semantic_package(semantic)

    response = connector.analyze(
        semantic,
        ConnectorAnalysisRequest(
            metric_id="revenue",
            dimensions=["region"],
            limit=10,
        ),
    )

    assert response.rows[0]["region"] == "East"
    assert float(response.rows[0]["revenue"]) == 175.0
    assert response.evidence.row_count == 2
    assert len(response.evidence.query_sha256) == 64
    assert response.evidence.semantic_hash == semantic.content_hash
    assert response.report.evidence.evidence_id == response.evidence.evidence_id
    assert "read-only" in response.report.limitations[0].lower()

    with pytest.raises(PermissionError):
        connector.validate_semantic_package(
            semantic.model_copy(update={"schema_name": "public"})
        )
