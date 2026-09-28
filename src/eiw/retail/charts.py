"""Business-story visualization planning for the retail BA Agent."""

from __future__ import annotations

from uuid import uuid4

from eiw.retail.models import ChartArtifact, Insight, WorkstreamName, WorkstreamResult


class ChartPlanner:
    def plan(
        self,
        workstreams: list[WorkstreamResult],
        insights: list[Insight],
    ) -> list[ChartArtifact]:
        by_name = {item.name: item for item in workstreams}
        charts: list[ChartArtifact] = []

        store = by_name.get(WorkstreamName.STORE)
        if store and store.rows:
            rows = store.rows[:10]
            charts.append(
                self._bar(
                    title="A small number of stores explain most of the sales movement",
                    subtitle="Largest store-level changes versus the comparison period",
                    categories=[str(row["segment"]) for row in rows],
                    values=[round(float(row["delta"]), 2) for row in rows],
                    series_name="Sales change",
                    insight_ids=[item.insight_id for item in insights if item.kind == "store_driver"][:4],
                )
            )

        product = by_name.get(WorkstreamName.PRODUCT)
        if product and product.rows:
            rows = product.rows[:10]
            charts.append(
                self._bar(
                    title="Commodity contribution isolates the largest business drivers",
                    subtitle="Largest commodity-level changes versus the comparison period",
                    categories=[str(row["segment"]) for row in rows],
                    values=[round(float(row["delta"]), 2) for row in rows],
                    series_name="Sales change",
                    insight_ids=[item.insight_id for item in insights if item.kind == "commodity_driver"][:4],
                )
            )

        promo = by_name.get(WorkstreamName.PROMOTION)
        if promo and promo.rows:
            rows = promo.rows[:8]
            charts.append(
                self._bar(
                    title="Merchandising states show materially different observed sales",
                    subtitle="Association only; use matched analysis before causal claims",
                    categories=[str(row["display_location"]) for row in rows],
                    values=[round(float(row["avg_line_sales"] or 0.0), 2) for row in rows],
                    series_name="Average line sales",
                    insight_ids=[item.insight_id for item in insights if item.kind == "merchandising"][:2],
                )
            )
        return [self._qa(chart) for chart in charts]

    def _bar(
        self,
        *,
        title: str,
        subtitle: str,
        categories: list[str],
        values: list[float],
        series_name: str,
        insight_ids: list[str],
    ) -> ChartArtifact:
        horizontal = len(categories) > 6
        if horizontal:
            option = {
                "title": {"text": title, "subtext": subtitle, "left": 0},
                "tooltip": {"trigger": "axis"},
                "grid": {"left": 140, "right": 30, "top": 86, "bottom": 40},
                "xAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#e8ecef"}}},
                "yAxis": {"type": "category", "data": categories, "axisTick": {"show": False}},
                "series": [{"name": series_name, "type": "bar", "data": values, "barMaxWidth": 22}],
            }
        else:
            option = {
                "title": {"text": title, "subtext": subtitle, "left": 0},
                "tooltip": {"trigger": "axis"},
                "grid": {"left": 70, "right": 30, "top": 86, "bottom": 70},
                "xAxis": {"type": "category", "data": categories, "axisLabel": {"rotate": 20}},
                "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#e8ecef"}}},
                "series": [{"name": series_name, "type": "bar", "data": values, "barMaxWidth": 28}],
            }
        return ChartArtifact(
            chart_id=f"chart-{uuid4().hex[:10]}",
            title=title,
            subtitle=subtitle,
            chart_type="bar",
            option=option,
            insight_ids=insight_ids,
        )

    def restyle(self, chart: ChartArtifact, instruction: str) -> ChartArtifact:
        """Apply safe presentation-only changes without mutating chart data."""
        normalized = instruction.lower()
        option = dict(chart.option)
        series = [dict(item) for item in option.get("series", [])]
        if not series:
            raise ValueError("chart has no series")

        wants_line = any(token in normalized for token in ("line", "折线", "趋势"))
        wants_bar = any(token in normalized for token in ("bar", "柱", "条形"))
        wants_horizontal = any(token in normalized for token in ("horizontal", "横", "排名"))

        if wants_line:
            for item in series:
                item["type"] = "line"
                item.pop("barMaxWidth", None)
                item["smooth"] = False
            option["series"] = series
            return self._qa(
                chart.model_copy(update={"chart_type": "line", "option": option})
            )

        if wants_bar:
            for item in series:
                item["type"] = "bar"
                item["barMaxWidth"] = 24
                item.pop("smooth", None)
            option["series"] = series

        if wants_horizontal:
            x_axis = dict(option.get("xAxis", {}))
            y_axis = dict(option.get("yAxis", {}))
            if x_axis.get("type") == "category":
                option["xAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#e8ecef"}}}
                option["yAxis"] = {"type": "category", "data": x_axis.get("data", []), "axisTick": {"show": False}}
                option["grid"] = {"left": 140, "right": 30, "top": 86, "bottom": 40}
            elif y_axis.get("type") == "category":
                pass

        return self._qa(chart.model_copy(update={"option": option}))

    def _qa(self, chart: ChartArtifact) -> ChartArtifact:
        option = dict(chart.option)
        title = dict(option.get("title", {}))
        if not title.get("text"):
            title["text"] = chart.title
        option["title"] = title
        series = list(option.get("series", []))
        if not series:
            raise ValueError(f"chart {chart.chart_id} has no series")
        return chart.model_copy(update={"option": option})
