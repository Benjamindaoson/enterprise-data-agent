"""Measured DuckDB access for the Iowa reference snapshot."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, cast

import duckdb


class DataUnavailable(RuntimeError):
    pass


METRICS = {
    "wholesale_sales_amount": {
        "label": "Wholesale sales",
        "unit": "USD",
        "expression": "SUM(line_wholesale_sales_amount)",
        "availability": "2024-01-01 onward",
        "description": "State wholesale purchase/order amount; not consumer POS revenue.",
    },
    "bottles_ordered": {
        "label": "Bottles ordered",
        "unit": "bottles",
        "expression": "SUM(bottles_ordered)",
        "availability": "2024-01-01 onward",
        "description": "Bottles on wholesale orders; not consumer units sold.",
    },
    "volume_liters": {
        "label": "Ordered volume",
        "unit": "liters",
        "expression": "SUM(ordered_volume_liters)",
        "availability": "2024-01-01 onward",
        "description": "Volume represented by wholesale orders.",
    },
    "average_wholesale_price_per_bottle": {
        "label": "Average wholesale price",
        "unit": "USD/bottle",
        "expression": "SUM(line_wholesale_sales_amount) / NULLIF(SUM(bottles_ordered), 0)",
        "availability": "2024-01-01 onward",
        "description": "Composite wholesale price per ordered bottle; mix-sensitive.",
    },
    "state_acquisition_cost": {
        "label": "State acquisition cost",
        "unit": "USD",
        "expression": "SUM(ROUND(state_cost_per_bottle * bottles_ordered, 2))",
        "availability": "2025-07-01 onward",
        "description": "Transaction-level state acquisition cost estimate.",
    },
    "wholesale_gross_spread": {
        "label": "Wholesale gross spread",
        "unit": "USD",
        "expression": "sales - acquisition cost",
        "availability": "2025-07-01 onward",
        "description": "Wholesale spread only; not store profit or net profit.",
    },
    "wholesale_spread_rate": {
        "label": "Wholesale spread rate",
        "unit": "%",
        "expression": "spread / sales",
        "availability": "2025-07-01 onward",
        "description": "Wholesale spread divided by wholesale sales.",
    },
}

DIMENSIONS = {
    "month": ("strftime(order_date, '%Y-%m')", "Month"),
    "year": ("year(order_date)", "Year"),
    "store": ("store_name_at_order", "Store"),
    "county": ("county_name_at_order", "County"),
    "vendor": ("vendor_name_at_order", "Vendor"),
    "category": ("category_name_at_order", "Category"),
    "product": ("product_name_at_order", "Product"),
    "city": ("city_at_order", "City"),
}


class IowaData:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(os.getenv("EIW_DATA_ROOT", "data/curated"))
        self.snapshot_id = "iowa_liquor_snapshot_2026_07_v1"
        self.directory = self.root / self.snapshot_id

    @property
    def fact_path(self) -> Path:
        return self.directory / "fact_liquor_order_line.parquet"

    @property
    def manifest_path(self) -> Path:
        return self.directory / "manifest.json"

    def available(self) -> bool:
        return self.fact_path.exists() and self.fact_path.stat().st_size > 0

    def manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {
                "snapshot_id": self.snapshot_id,
                "status": "NOT_BUILT",
                "warning": "Curated Parquet is not available. Run `make data`.",
            }
        return cast(dict[str, Any], json.loads(self.manifest_path.read_text()))

    def status(self) -> dict[str, Any]:
        manifest = self.manifest()
        manifest["available"] = self.available()
        if self.available():
            con = self.connection()
            row = con.execute("SELECT count(*), min(order_date), max(order_date) FROM fact").fetchone()
            if row is None:
                raise DataUnavailable("Unable to profile the curated snapshot.")
            manifest["measured_row_count"] = row[0]
            manifest["measured_business_date_min"] = str(row[1])
            manifest["measured_business_date_max"] = str(row[2])
        return manifest

    def connection(self) -> duckdb.DuckDBPyConnection:
        if not self.available():
            raise DataUnavailable("The curated Iowa snapshot is not available; run `make data` first.")
        con = duckdb.connect()
        quoted_path = "'" + str(self.fact_path).replace("'", "''") + "'"
        con.execute(f"CREATE VIEW fact AS SELECT * FROM read_parquet({quoted_path})")
        return con

    @staticmethod
    def _rows(result: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
        columns = [item[0] for item in result.description]
        values = result.fetchall()
        output = []
        for row in values:
            item = {}
            for key, value in zip(columns, row, strict=True):
                if hasattr(value, "isoformat"):
                    value = value.isoformat()
                elif isinstance(value, float):
                    value = round(value, 6)
                item[key] = value
            output.append(item)
        return output

    def aggregate(
        self,
        start: date,
        end: date,
        metric_ids: list[str],
        dimension: str | None = None,
        filters: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        filters = filters or {}
        expressions: list[str] = []
        for metric_id in metric_ids:
            if metric_id == "wholesale_sales_amount":
                expressions.append("SUM(line_wholesale_sales_amount) AS wholesale_sales_amount")
            elif metric_id == "bottles_ordered":
                expressions.append("SUM(bottles_ordered) AS bottles_ordered")
            elif metric_id == "volume_liters":
                expressions.append("SUM(ordered_volume_liters) AS volume_liters")
            elif metric_id == "average_wholesale_price_per_bottle":
                expressions.append("SUM(line_wholesale_sales_amount) / NULLIF(SUM(bottles_ordered), 0) AS average_wholesale_price_per_bottle")
            elif metric_id == "state_acquisition_cost":
                expressions.append("SUM(ROUND(state_cost_per_bottle * bottles_ordered, 2)) AS state_acquisition_cost")
            elif metric_id == "wholesale_gross_spread":
                expressions.extend([
                    "SUM(line_wholesale_sales_amount) AS wholesale_sales_amount",
                    "SUM(ROUND(state_cost_per_bottle * bottles_ordered, 2)) AS state_acquisition_cost",
                    "SUM(line_wholesale_sales_amount) - SUM(ROUND(state_cost_per_bottle * bottles_ordered, 2)) AS wholesale_gross_spread",
                ])
            elif metric_id == "wholesale_spread_rate":
                expressions.append("(SUM(line_wholesale_sales_amount) - SUM(ROUND(state_cost_per_bottle * bottles_ordered, 2))) / NULLIF(SUM(line_wholesale_sales_amount), 0) AS wholesale_spread_rate")
        expressions = list(dict.fromkeys(expressions))
        select_dimension = ""
        group_by = ""
        if dimension:
            if dimension not in DIMENSIONS:
                raise ValueError(f"Unsupported dimension: {dimension}")
            select_dimension = f"{DIMENSIONS[dimension][0]} AS dimension_value,"
            expression_text = ",".join(expressions)
            order_alias = "wholesale_sales_amount" if "wholesale_sales_amount" in expression_text else "bottles_ordered" if "bottles_ordered" in expression_text else "dimension_value"
            group_by = f"GROUP BY 1 ORDER BY ABS({order_alias}) DESC NULLS LAST"
        where = ["order_date >= ?", "order_date <= ?"]
        params: list[Any] = [start, end]
        for field, value in filters.items():
            mapping = {"county": "county_name_at_order", "store": "store_name_at_order", "vendor": "vendor_name_at_order", "category": "category_name_at_order", "product": "product_name_at_order"}
            if field in mapping:
                where.append(f"LOWER({mapping[field]}) LIKE LOWER(?)")
                params.append(f"%{value}%")
        sql = f"SELECT {select_dimension} {', '.join(expressions)} FROM fact WHERE {' AND '.join(where)} {group_by}"
        con = self.connection()
        try:
            return self._rows(con.execute(sql, params))
        finally:
            con.close()

    def monthly_trend(self, start: date, end: date, metric_ids: list[str]) -> list[dict[str, Any]]:
        return self.aggregate(start, end, metric_ids, "month")

    def distinct_values(self, dimension: str, limit: int = 100) -> list[str]:
        if dimension not in DIMENSIONS:
            raise ValueError(f"Unsupported dimension: {dimension}")
        con = self.connection()
        try:
            rows = con.execute(f"SELECT DISTINCT {DIMENSIONS[dimension][0]} FROM fact WHERE {DIMENSIONS[dimension][0]} IS NOT NULL ORDER BY 1 LIMIT ?", [limit]).fetchall()
            return [str(row[0]) for row in rows]
        finally:
            con.close()
