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
def test_postgres_connector_executes_bounded_derived_metrics() -> None:
    database_url = os.getenv("EIW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("EIW_TEST_DATABASE_URL is required for PostgreSQL integration")

    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS derived_demo CASCADE"))
        connection.execute(text("CREATE SCHEMA derived_demo"))
        connection.execute(
            text(
                """
                CREATE TABLE derived_demo.transactions (
                    invoice TEXT NOT NULL,
                    customer_id TEXT,
                    country TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price NUMERIC(12, 2) NOT NULL,
                    converted BOOLEAN NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO derived_demo.transactions
                    (invoice, customer_id, country, quantity, unit_price, converted)
                VALUES
                    ('A', 'C1', 'UK', 2, 10.00, TRUE),
                    ('B', 'C1', 'UK', 1, 5.00, FALSE),
                    ('C', 'C2', 'UK', 3, 4.00, TRUE),
                    ('D', 'C3', 'FR', 2, 7.50, FALSE)
                """
            )
        )

    connector = EnterprisePostgresConnector(
        database_url,
        policy=PostgresPermissionPolicy(
            allowed_schemas={"derived_demo"},
            allowed_tables={"derived_demo.transactions"},
            allowed_columns={
                "derived_demo.transactions": {
                    "invoice",
                    "customer_id",
                    "country",
                    "quantity",
                    "unit_price",
                    "converted",
                }
            },
        ),
    )
    package = PostgresSemanticPackage(
        package_id="derived",
        version="1",
        schema_name="derived_demo",
        metrics={
            "revenue": PostgresMetric(
                table="transactions",
                column="quantity",
                columns=["quantity", "unit_price"],
                operator="multiply",
                aggregation="sum",
            ),
            "active_customers": PostgresMetric(
                table="transactions",
                column="customer_id",
                aggregation="count_distinct",
            ),
            "conversion_rate": PostgresMetric(
                table="transactions",
                column="converted",
                aggregation="rate_equals",
                predicate_value=True,
            ),
        },
        dimensions={
            "country": PostgresDimension(
                table="transactions",
                column="country",
            )
        },
    )

    revenue = connector.analyze(
        package,
        ConnectorAnalysisRequest(
            metric_id="revenue",
            dimensions=["country"],
        ),
    )
    by_country = {
        row["country"]: float(row["revenue"])
        for row in revenue.rows
    }
    assert by_country == {"UK": 37.0, "FR": 15.0}

    customers = connector.analyze(
        package,
        ConnectorAnalysisRequest(
            metric_id="active_customers",
            dimensions=["country"],
        ),
    )
    customer_counts = {
        row["country"]: int(row["active_customers"])
        for row in customers.rows
    }
    assert customer_counts == {"UK": 2, "FR": 1}


    conversions = connector.analyze(
        package,
        ConnectorAnalysisRequest(
            metric_id="conversion_rate",
            dimensions=["country"],
        ),
    )
    conversion_rates = {
        row["country"]: float(row["conversion_rate"])
        for row in conversions.rows
    }
    assert conversion_rates["UK"] == pytest.approx(2 / 3)
    assert conversion_rates["FR"] == pytest.approx(0.0)
    assert (
        conversions.evidence.parameters["metric:conversion_rate:predicate"]
        is True
    )
