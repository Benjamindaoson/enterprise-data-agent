from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from eiw.ontology.benchmark import BlindOnboardingBenchmark, blind_connector


@pytest.mark.integration
def test_blind_onboarding_benchmark_promotes_evolved_ontology() -> None:
    database_url = os.getenv("EIW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("EIW_TEST_DATABASE_URL is required for PostgreSQL integration")

    engine = create_engine(database_url, future=True)
    schema = "blind_online_retail"
    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(
            text(
                f"""
                CREATE TABLE "{schema}".transactions (
                    "InvoiceNo" TEXT NOT NULL,
                    "StockCode" TEXT NOT NULL,
                    "Description" TEXT,
                    "Quantity" INTEGER NOT NULL,
                    "InvoiceDate" TIMESTAMP,
                    "UnitPrice" NUMERIC(14, 4) NOT NULL,
                    "CustomerID" TEXT,
                    "Country" TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                INSERT INTO "{schema}".transactions
                    ("InvoiceNo", "StockCode", "Description", "Quantity",
                     "InvoiceDate", "UnitPrice", "CustomerID", "Country")
                VALUES
                    ('A1', 'SKU-1', 'Item 1', 2, NOW(), 10.00, 'C1', 'UK'),
                    ('A2', 'SKU-2', 'Item 2', 1, NOW(), 5.00, 'C1', 'UK'),
                    ('A3', 'SKU-1', 'Item 1', 3, NOW(), 4.00, 'C2', 'UK'),
                    ('A4', 'SKU-3', 'Item 3', 2, NOW(), 7.50, 'C3', 'France'),
                    ('A5', 'SKU-3', 'Item 3', 4, NOW(), 8.00, 'C4', 'France')
                """
            )
        )

    connector = blind_connector(database_url)
    result = BlindOnboardingBenchmark(
        connector,
        schema_name=schema,
        table_name="transactions",
    ).run()

    assert result["gate"]["promoted"] is True, result["gate"]
    assert all(result["assertions"].values())
    evolved = result["lanes"]["evolved_ontology"]
    static = result["lanes"]["static_semantic_package"]
    assert evolved["semantic_coverage"] > static["semantic_coverage"]
    assert evolved["task_success"] > static["task_success"]
    assert evolved["correct_abstention"] == 1.0
