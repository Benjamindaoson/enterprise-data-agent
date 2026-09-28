import asyncio
import os

import pytest
from sqlalchemy import text

from eiw.connectors.postgres import (
    PostgresAnalysisRequest,
    PostgresConnectorConfig,
    PostgresDimensionSpec,
    PostgresDomainRuntime,
    PostgresEnterpriseConnector,
    PostgresMetricSpec,
    PostgresSemanticConfig,
)
from eiw.production.persistence import ProductionStore
from eiw.production.queue import RedisTaskQueue, TaskEnvelope


@pytest.mark.integration
def test_postgres_trajectory_checkpoint_and_approval_round_trip():
    database_url = os.getenv("EIW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("EIW_TEST_DATABASE_URL not configured")
    store = ProductionStore(database_url)
    task_id = "integration-task"
    trajectory_id = "integration-trajectory"
    store.purge_task(task_id)

    store.append_trajectory_event(
        trajectory_id=trajectory_id,
        task_id=task_id,
        step_index=0,
        payload={"action": "inspect_metric"},
    )
    store.append_trajectory_event(
        trajectory_id=trajectory_id,
        task_id=task_id,
        step_index=1,
        payload={"action": "cross_check"},
    )
    assert [row["step_index"] for row in store.load_trajectory(trajectory_id)] == [0, 1]

    store.save_checkpoint(task_id=task_id, version=1, payload={"step": 2})
    checkpoint = store.load_checkpoint(task_id)
    assert checkpoint is not None
    assert checkpoint["version"] == 1
    assert checkpoint["payload"]["step"] == 2

    approval_id = store.request_approval(
        task_id=task_id,
        action_id="campaign-write",
        requested_by="agent",
    )
    store.decide_approval(approval_id, approved=True, decided_by="human-reviewer")
    approval = store.get_approval(approval_id)
    assert approval is not None
    assert approval["status"] == "APPROVED"


@pytest.mark.integration
def test_redis_queue_round_trip():
    redis_url = os.getenv("EIW_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("EIW_TEST_REDIS_URL not configured")

    async def run() -> None:
        queue = RedisTaskQueue(redis_url, key="eiw:test:tasks")
        await queue.redis.delete(queue.key)
        await queue.put(TaskEnvelope("t1", "analysis", {"question": "why"}))
        item = await queue.get(timeout=2)
        assert item.task_id == "t1"
        assert item.payload["question"] == "why"
        await queue.close()

    asyncio.run(run())



@pytest.mark.integration
def test_postgres_enterprise_connector_full_chain():
    database_url = os.getenv("EIW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("EIW_TEST_DATABASE_URL not configured")

    connector = PostgresEnterpriseConnector(
        database_url,
        config=PostgresConnectorConfig(
            allowed_schemas=["public"],
            allowed_tables=["enterprise_sales_fixture"],
            denied_columns=["secret_note"],
            max_rows=25,
        ),
    )
    with connector.engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS enterprise_sales_fixture"))
        connection.execute(
            text(
                """
                CREATE TABLE enterprise_sales_fixture (
                    id INTEGER PRIMARY KEY,
                    region TEXT NOT NULL,
                    product TEXT NOT NULL,
                    revenue NUMERIC NOT NULL,
                    units INTEGER NOT NULL,
                    secret_note TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO enterprise_sales_fixture
                    (id, region, product, revenue, units, secret_note)
                VALUES
                    (1, 'East', 'A', 120.0, 12, 'hidden'),
                    (2, 'East', 'B', 80.0, 8, 'hidden'),
                    (3, 'West', 'A', 90.0, 9, 'hidden'),
                    (4, 'West', 'B', 60.0, 6, 'hidden')
                """
            )
        )

    semantic = PostgresSemanticConfig(
        package_id="enterprise-sales-test",
        title="Enterprise Sales Test",
        fact_table="enterprise_sales_fixture",
        metrics=[
            PostgresMetricSpec(
                id="revenue",
                label="Revenue",
                column="revenue",
                aggregation="sum",
                unit="USD",
            ),
            PostgresMetricSpec(
                id="units",
                label="Units",
                column="units",
                aggregation="sum",
                unit="unit",
            ),
        ],
        dimensions=[
            PostgresDimensionSpec(id="region", label="Region", column="region"),
            PostgresDimensionSpec(id="product", label="Product", column="product"),
        ],
        role_metric_allowlist={
            "analyst": ["revenue", "units"],
            "viewer": ["units"],
        },
    )

    try:
        domain = PostgresDomainRuntime(connector, semantic)
        assert connector.ping() is True
        table = domain.catalog.tables[0]
        assert table.table_name == "enterprise_sales_fixture"
        assert "secret_note" not in {column.name for column in table.columns}
        assert domain.semantic_package.content_hash

        response = domain.analyze(
            PostgresAnalysisRequest(
                question="Show Revenue by Region",
                role="analyst",
                top_k=10,
            )
        )
        assert response.status == "COMPLETED"
        assert response.metric_id == "revenue"
        assert response.dimension_ids == ["region"]
        assert response.rows[0]["region"] == "East"
        assert float(response.rows[0]["revenue"]) == 200.0
        assert response.evidence["read_only"] is True
        assert response.evidence["catalog_hash"] == domain.catalog.catalog_hash
        assert (
            response.evidence["semantic_content_hash"]
            == domain.semantic_package.content_hash
        )
        assert response.report["executive_summary"]

        with pytest.raises(PermissionError):
            domain.analyze(
                PostgresAnalysisRequest(
                    question="Show Revenue by Region",
                    role="viewer",
                )
            )
    finally:
        with connector.engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS enterprise_sales_fixture"))
