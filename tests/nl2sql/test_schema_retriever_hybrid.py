"""Integration tests for hybrid retrieval inside SchemaRetriever."""

from types import SimpleNamespace

from eiw.nl2sql.schema_retriever import SchemaRetriever


def _classification():
    return SimpleNamespace(value="INTERNAL")


def _metric(metric_id: str, name: str, aliases: list[str], column: str):
    return SimpleNamespace(
        id=metric_id,
        name=name,
        aliases=aliases,
        description=f"{name} business metric",
        business_context=f"Use {name} for governed analysis",
        source_table="fact_sales",
        source_columns=[column],
        classification=_classification(),
        formula=SimpleNamespace(expression=column),
        allowed_join_paths=[],
    )


def _dimension(dimension_id: str, name: str, aliases: list[str], column: str):
    return SimpleNamespace(
        id=dimension_id,
        name=name,
        aliases=aliases,
        description=f"{name} business dimension",
        source_table="fact_sales",
        source_column=column,
        classification=_classification(),
        policy_tags=[],
        join_paths=[],
    )


class FakePackage:
    def __init__(self) -> None:
        self.metrics = [
            _metric("net_sales", "Net Sales", ["revenue", "sales"], "amount"),
            _metric("units", "Units", ["quantity"], "units"),
        ]
        self.dimensions = [
            _dimension("region", "Region", ["territory"], "region"),
            _dimension("channel", "Channel", ["sales channel"], "channel"),
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


def test_question_retrieval_populates_governed_schema_context() -> None:
    retriever = SchemaRetriever({"sales": FakePackage()})
    schema = retriever.retrieve(
        domain="sales",
        question="show revenue by region",
        user_roles=["analyst"],
        business_context={"schema_candidate_budget": 3},
    )

    assert "fact_sales" in schema.tables
    assert "net_sales" in schema.retrieval_trace["selected_metrics"]
    assert "region" in schema.retrieval_trace["selected_dimensions"]
    assert schema.retrieval_trace["mode"] == "hybrid_rerank"
    assert schema.retrieval_trace["hits"]


def test_explicit_semantic_links_are_protected_from_retrieval_pruning() -> None:
    retriever = SchemaRetriever({"sales": FakePackage()})
    schema = retriever.retrieve(
        domain="sales",
        metrics=["units"],
        dimensions=["channel"],
        question="revenue by region",
        business_context={"schema_candidate_budget": 1},
    )

    assert "units" in schema.retrieval_trace["protected_metrics"]
    assert "channel" in schema.retrieval_trace["protected_dimensions"]
    assert "units" in schema.retrieval_trace["selected_metrics"]
    assert "channel" in schema.retrieval_trace["selected_dimensions"]

    column_names = {
        column.name
        for column in schema.tables["fact_sales"].columns
    }
    assert "units" in column_names
    assert "channel" in column_names


def test_explicit_only_mode_remains_backward_compatible() -> None:
    retriever = SchemaRetriever({"sales": FakePackage()})
    schema = retriever.retrieve(
        domain="sales",
        metrics=["net_sales"],
        dimensions=["region"],
    )

    assert schema.retrieval_trace["mode"] == "explicit_only"
    assert schema.retrieval_trace["selected_metrics"] == ["net_sales"]
    assert schema.retrieval_trace["selected_dimensions"] == ["region"]
