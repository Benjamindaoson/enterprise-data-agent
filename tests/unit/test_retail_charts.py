from eiw.retail.charts import ChartPlanner
from eiw.retail.models import ChartArtifact


def test_chart_restyle_changes_presentation_without_changing_values() -> None:
    chart = ChartArtifact(
        chart_id="c1",
        title="Store ranking",
        chart_type="bar",
        option={
            "xAxis": {"type": "category", "data": ["A", "B"]},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": [10, 20]}],
        },
    )

    restyled = ChartPlanner().restyle(chart, "换成折线图")

    assert restyled.chart_type == "line"
    assert restyled.option["series"][0]["type"] == "line"
    assert restyled.option["series"][0]["data"] == [10, 20]
