"""End-to-end contract tests for the converged NL2SQL service."""

from types import SimpleNamespace

from eiw.nl2sql.contracts import ExecutionStatus, NL2SQLRequest, QueryLane
from eiw.nl2sql.service import NL2SQLConfig, NL2SQLService


def _classification():
    return SimpleNamespace(value="INTERNAL")


class FakePackage:
    def __init__(self) -> None:
        self.package = SimpleNamespace(id="sales")
        self.metrics = [
            SimpleNamespace(
                id="net_sales",
                name="Net Sales",
                aliases=["revenue", "sales"],
                description="Governed net sales",
                business_context="Use for revenue questions",
                source_table="fact_sales",
                source_columns=["amount"],
                classification=_classification(),
                formula=SimpleNamespace(
                    expression="amount",
                    type="column",
                    base_metrics=[],
                ),
                aggregation=SimpleNamespace(value="SUM"),
                allowed_join_paths=[],
                required_dimensions=[],
                incompatible_dimensions=[],
            )
        ]
        self.dimensions = [
            SimpleNamespace(
                id="region",
                name="Region",
                aliases=["territory"],
                description="Sales region",
                source_table="fact_sales",
                source_column="region",
                classification=_classification(),
                policy_tags=[],
                join_paths=[],
            )
        ]
        self.join_policies = []

    def metric(self, metric_id: str):
        for metric in self.metrics:
            if metric.id == metric_id:
                return metric
        raise KeyError(metric_id)

    def dimension(self, dimension_id: str):
        for dimension in self.dimensions:
            if dimension.id == dimension_id:
                return dimension
        raise KeyError(dimension_id)


def test_service_executes_semantic_plan_end_to_end() -> None:
    service = NL2SQLService(
        config=NL2SQLConfig(
            default_lane=QueryLane.DETERMINISTIC,
            enable_cost_guard=False,
            allow_empty_results=False,
        ),
        semantic_packages={"sales": FakePackage()},
    )
    service._example_retriever.retrieve = lambda **_: SimpleNamespace(examples=[])

    service._executor._conn.execute(
        "CREATE TABLE fact_sales(region VARCHAR, amount DOUBLE)"
    )
    service._executor._conn.execute(
        "INSERT INTO fact_sales VALUES ('east', 10), ('east', 5), ('west', 7)"
    )

    result = service.execute(
        NL2SQLRequest(
            question="total revenue by region",
            domain="sales",
            resolved_metrics=["net_sales"],
            resolved_dimensions=["region"],
            user_roles=["analyst"],
        )
    )

    assert result.final_status == ExecutionStatus.VALID
    assert result.success is True
    assert result.generated_sql is not None
    assert "SUM(amount) AS net_sales" in result.generated_sql.sql
    assert "GROUP BY region" in result.generated_sql.sql
    assert result.execution is not None
    assert result.execution.row_count == 2


def test_unknown_domain_is_explicitly_rejected() -> None:
    service = NL2SQLService()
    result = service.execute(
        NL2SQLRequest(
            question="show revenue",
            domain="missing-domain",
        )
    )

    assert result.final_status == ExecutionStatus.REJECTED
    assert result.validation is not None
    assert "No semantic package registered" in result.validation.details
