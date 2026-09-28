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

        if store:
            cross_scan = self._artifact_rows(store, "store_commodity_scan")
            if cross_scan:
                charts.append(
                    self._heatmap(
                        title="Store × commodity heatmap exposes concentrated pockets of change",
                        subtitle="Largest scanned sales movements versus the comparison period",
                        rows=cross_scan[:24],
                        insight_ids=[
                            item.insight_id
                            for item in insights
                            if item.kind == "cross_dimension_driver"
                        ][:5],
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

        if product:
            decomposition = self._artifact_rows(product, "price_volume_decomposition")
            if decomposition:
                charts.append(
                    self._price_volume_chart(
                        rows=decomposition[:8],
                        insight_ids=[
                            item.insight_id
                            for item in insights
                            if item.kind == "price_volume"
                        ][:4],
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

        customer = by_name.get(WorkstreamName.CUSTOMER)
        if customer:
            income_rows = self._artifact_rows(customer, "demographic_income")
            if income_rows:
                rows = income_rows[:10]
                charts.append(
                    self._bar(
                        title="Customer income segments show different period movements",
                        subtitle="Descriptive customer-mix analysis; not causal attribution",
                        categories=[str(row["segment"]) for row in rows],
                        values=[round(float(row["delta"] or 0.0), 2) for row in rows],
                        series_name="Sales change",
                        insight_ids=[
                            item.insight_id
                            for item in insights
                            if item.kind == "customer_segment_driver"
                        ][:3],
                    )
                )

            coupon_rows = self._artifact_rows(customer, "coupon_funnel")
            if coupon_rows:
                rows = coupon_rows[:10]
                charts.append(
                    self._bar(
                        title="Observed coupon redemption varies materially by campaign",
                        subtitle="Targeting-to-redemption funnel; not incremental lift",
                        categories=[str(row["campaign_id"]) for row in rows],
                        values=[
                            round(float(row["household_redemption_rate"] or 0.0) * 100.0, 2)
                            for row in rows
                        ],
                        series_name="Household redemption rate (%)",
                        insight_ids=[
                            item.insight_id
                            for item in insights
                            if item.kind == "coupon_funnel"
                        ][:2],
                    )
                )
        return [self._qa(chart) for chart in charts]

    @staticmethod
    def _artifact_rows(result: WorkstreamResult, artifact_type: str) -> list[dict[str, object]]:
        for artifact in result.artifacts:
            if artifact.get("type") == artifact_type:
                return list(artifact.get("rows", []))
        return []

    def _heatmap(
        self,
        *,
        title: str,
        subtitle: str,
        rows: list[dict[str, object]],
        insight_ids: list[str],
    ) -> ChartArtifact:
        stores = list(dict.fromkeys(str(row["store_id"]) for row in rows))
        commodities = list(dict.fromkeys(str(row["commodity"]) for row in rows))
        store_index = {value: index for index, value in enumerate(stores)}
        commodity_index = {value: index for index, value in enumerate(commodities)}
        data = [
            [
                commodity_index[str(row["commodity"])],
                store_index[str(row["store_id"])],
                round(float(row.get("sales_delta") or 0.0), 2),
            ]
            for row in rows
        ]
        magnitudes = [abs(float(item[2])) for item in data]
        bound = max(magnitudes) if magnitudes else 1.0
        option = {
            "title": {"text": title, "subtext": subtitle, "left": 0},
            "tooltip": {"position": "top"},
            "grid": {"left": 80, "right": 30, "top": 92, "bottom": 90},
            "xAxis": {
                "type": "category",
                "data": commodities,
                "axisLabel": {"rotate": 25},
                "splitArea": {"show": True},
            },
            "yAxis": {
                "type": "category",
                "data": stores,
                "splitArea": {"show": True},
            },
            "visualMap": {
                "min": -bound,
                "max": bound,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": 8,
            },
            "series": [
                {
                    "name": "Sales change",
                    "type": "heatmap",
                    "data": data,
                    "label": {"show": False},
                }
            ],
        }
        return ChartArtifact(
            chart_id=f"chart-{uuid4().hex[:10]}",
            title=title,
            subtitle=subtitle,
            chart_type="heatmap",
            option=option,
            insight_ids=insight_ids,
        )

    def _price_volume_chart(
        self,
        *,
        rows: list[dict[str, object]],
        insight_ids: list[str],
    ) -> ChartArtifact:
        categories = [str(row["commodity"]) for row in rows]
        volume = [round(float(row.get("volume_effect") or 0.0), 2) for row in rows]
        price = [round(float(row.get("price_effect") or 0.0), 2) for row in rows]
        option = {
            "title": {
                "text": "Price and volume effects explain how commodity sales moved",
                "subtext": "Deterministic decomposition; the two effects reconcile sales change",
                "left": 0,
            },
            "tooltip": {"trigger": "axis"},
            "legend": {"top": 52},
            "grid": {"left": 70, "right": 25, "top": 92, "bottom": 80},
            "xAxis": {"type": "category", "data": categories, "axisLabel": {"rotate": 24}},
            "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#e8ecef"}}},
            "series": [
                {"name": "Volume effect", "type": "bar", "data": volume, "barMaxWidth": 24},
                {"name": "Price effect", "type": "bar", "data": price, "barMaxWidth": 24},
            ],
        }
        return ChartArtifact(
            chart_id=f"chart-{uuid4().hex[:10]}",
            title="Price and volume effects explain how commodity sales moved",
            subtitle="Deterministic decomposition",
            chart_type="bar",
            option=option,
            insight_ids=insight_ids,
        )

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
