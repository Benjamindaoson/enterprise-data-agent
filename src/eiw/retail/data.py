"""DuckDB-backed retail analytical data plane.

The first reference schema targets dunnhumby / 84.51° Complete Journey. The
adapter accepts the common public file names and normalizes them into stable
views used by the BA Agent. The same analytical contracts are exercised against
an in-memory deterministic fixture in CI.
"""

from __future__ import annotations

from collections.abc import Iterable
import json
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

import duckdb


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _records(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [item[0] for item in cursor.description or []]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


class RetailDataEngine:
    """Stable analytical data interface for retail BA workloads."""

    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection,
        *,
        label: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._conn = connection
        self.label = label
        self.metadata = dict(metadata or {})

    @classmethod
    def demo(cls) -> RetailDataEngine:
        conn = duckdb.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE retail_products (
                product_id INTEGER,
                department VARCHAR,
                commodity VARCHAR,
                sub_commodity VARCHAR,
                brand VARCHAR
            )
            """
        )
        products = [
            (101, "BEAUTY", "SUN CARE", "SUNSCREEN", "A"),
            (102, "BEAUTY", "SUN CARE", "SUNSCREEN", "B"),
            (103, "BEAUTY", "SKIN CARE", "MASK", "C"),
            (104, "HEALTH", "VITAMINS", "MULTIVITAMIN", "D"),
            (105, "BEAUTY", "SUN CARE", "SUNSCREEN", "E"),
            (106, "PERSONAL", "HAIR CARE", "SHAMPOO", "F"),
        ]
        conn.executemany("INSERT INTO retail_products VALUES (?, ?, ?, ?, ?)", products)
        conn.execute(
            """
            CREATE TABLE retail_transactions (
                basket_id BIGINT,
                household_key INTEGER,
                week_no INTEGER,
                product_id INTEGER,
                quantity DOUBLE,
                sales_value DOUBLE,
                store_id INTEGER,
                retail_disc DOUBLE,
                coupon_disc DOUBLE,
                coupon_match_disc DOUBLE
            )
            """
        )
        rows: list[tuple[Any, ...]] = []
        basket = 10_000
        for week in range(1, 9):
            for store in range(1, 5):
                for household in range(1, 13):
                    basket += 1
                    for product_id in (101, 103, 104, 105):
                        base_qty = 2.0 + ((store + household + product_id + week) % 3)
                        if week >= 7 and store in {3, 4} and product_id in {101, 105}:
                            base_qty *= 0.35
                        if week >= 7 and store == 2 and product_id == 103:
                            base_qty *= 1.35
                        price = {101: 12.0, 103: 8.0, 104: 15.0, 105: 10.0}[product_id]
                        retail_disc = -1.5 if week in {3, 4, 7} and product_id in {101, 103} else 0.0
                        sales = max(0.0, base_qty * price + retail_disc)
                        rows.append(
                            (
                                basket,
                                household,
                                week,
                                product_id,
                                base_qty,
                                round(sales, 2),
                                store,
                                retail_disc,
                                0.0,
                                0.0,
                            )
                        )
        conn.executemany(
            "INSERT INTO retail_transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.execute(
            """
            CREATE TABLE retail_promotions (
                product_id INTEGER,
                store_id INTEGER,
                week_no INTEGER,
                display_location VARCHAR,
                mailer_location VARCHAR
            )
            """
        )
        promos: list[tuple[Any, ...]] = []
        for week in range(1, 9):
            for store in range(1, 5):
                for product_id in (101, 103, 104, 105):
                    display = "FRONT END CAP" if product_id in {101, 103} and week in {3, 4, 7} else "NO DISPLAY"
                    if product_id == 105 and week >= 7 and store in {3, 4}:
                        display = "NO DISPLAY"
                    mailer = "A" if week in {3, 4} and product_id in {101, 103} else "NONE"
                    promos.append((product_id, store, week, display, mailer))
        conn.executemany("INSERT INTO retail_promotions VALUES (?, ?, ?, ?, ?)", promos)
        return cls(
            conn,
            label="retail-demo-fixture",
            metadata={"source": "deterministic-ci-fixture", "license": "project-test-data"},
        )

    @classmethod
    def from_complete_journey(cls, root: Path) -> RetailDataEngine:
        """Load either the original dunnhumby CSV schema or completejourney CC0 Parquet.

        Supported inputs:
        - original source files: transaction_data.csv / product.csv / causal_data.csv;
        - normalized files produced by scripts/fetch_completejourney_cc0.py:
          transactions.parquet / products.parquet / promotions.parquet.

        The two public distributions use different column names. This adapter
        resolves both into one stable first-party schema.
        """

        root = root.expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(root)

        def find(*names: str) -> Path:
            for name in names:
                path = root / name
                if path.exists():
                    return path
            raise FileNotFoundError(f"None of {names!r} found under {root}")

        def reader(path: Path) -> str:
            if path.suffix.lower() == ".parquet":
                return f"read_parquet({_sql_literal(str(path))})"
            return f"read_csv_auto({_sql_literal(str(path))}, header=true, sample_size=-1)"

        def columns(connection: duckdb.DuckDBPyConnection, relation: str) -> dict[str, str]:
            rows = connection.execute(f'DESCRIBE "{relation}"').fetchall()
            return {str(row[0]).lower(): str(row[0]) for row in rows}

        def quote(name: str) -> str:
            return '"' + name.replace('"', '""') + '"'

        def pick(
            available: dict[str, str],
            *aliases: str,
            required: bool = True,
        ) -> str | None:
            for alias in aliases:
                resolved = available.get(alias.lower())
                if resolved is not None:
                    return quote(resolved)
            if required:
                raise ValueError(
                    f"Complete Journey source is missing required column; expected one of {aliases!r}"
                )
            return None

        def number_or_zero(column: str | None) -> str:
            if column is None:
                return "CAST(0 AS DOUBLE)"
            return f"COALESCE(CAST({column} AS DOUBLE), 0)"

        tx = find(
            "transaction_data.csv",
            "transactions.csv",
            "transaction_data.parquet",
            "transactions.parquet",
        )
        products = find("product.csv", "products.csv", "product.parquet", "products.parquet")
        causal = find(
            "causal_data.csv",
            "promotions.csv",
            "causal_data.parquet",
            "promotions.parquet",
        )

        conn = duckdb.connect(":memory:")
        conn.execute(f"CREATE VIEW source_transactions AS SELECT * FROM {reader(tx)}")
        conn.execute(f"CREATE VIEW source_products AS SELECT * FROM {reader(products)}")
        conn.execute(f"CREATE VIEW source_promotions AS SELECT * FROM {reader(causal)}")

        tx_columns = columns(conn, "source_transactions")
        product_columns = columns(conn, "source_products")
        promo_columns = columns(conn, "source_promotions")

        basket = pick(tx_columns, "BASKET_ID", "basket_id")
        household = pick(tx_columns, "HOUSEHOLD_KEY", "household_id")
        week = pick(tx_columns, "WEEK_NO", "week")
        product = pick(tx_columns, "PRODUCT_ID", "product_id")
        quantity = pick(tx_columns, "QUANTITY", "quantity")
        sales = pick(tx_columns, "SALES_VALUE", "sales_value")
        store = pick(tx_columns, "STORE_ID", "store_id")
        retail_disc = pick(tx_columns, "RETAIL_DISC", "retail_disc", required=False)
        coupon_disc = pick(tx_columns, "COUPON_DISC", "coupon_disc", required=False)
        coupon_match_disc = pick(
            tx_columns,
            "COUPON_MATCH_DISC",
            "coupon_match_disc",
            required=False,
        )

        conn.execute(
            f"""
            CREATE VIEW retail_transactions AS
            SELECT
                CAST({basket} AS BIGINT) AS basket_id,
                CAST({household} AS INTEGER) AS household_key,
                CAST({week} AS INTEGER) AS week_no,
                CAST({product} AS INTEGER) AS product_id,
                CAST({quantity} AS DOUBLE) AS quantity,
                CAST({sales} AS DOUBLE) AS sales_value,
                CAST({store} AS INTEGER) AS store_id,
                {number_or_zero(retail_disc)} AS retail_disc,
                {number_or_zero(coupon_disc)} AS coupon_disc,
                {number_or_zero(coupon_match_disc)} AS coupon_match_disc
            FROM source_transactions
            """
        )

        product_id = pick(product_columns, "PRODUCT_ID", "product_id")
        department = pick(product_columns, "DEPARTMENT", "department")
        commodity = pick(
            product_columns,
            "COMMODITY_DESC",
            "commodity",
            "commodity_desc",
            "product_category",
        )
        sub_commodity = pick(
            product_columns,
            "SUB_COMMODITY_DESC",
            "sub_commodity",
            "sub_commodity_desc",
            "product_type",
        )
        brand = pick(product_columns, "BRAND", "brand")
        conn.execute(
            f"""
            CREATE VIEW retail_products AS
            SELECT
                CAST({product_id} AS INTEGER) AS product_id,
                CAST({department} AS VARCHAR) AS department,
                CAST({commodity} AS VARCHAR) AS commodity,
                CAST({sub_commodity} AS VARCHAR) AS sub_commodity,
                CAST({brand} AS VARCHAR) AS brand
            FROM source_products
            """
        )

        promo_product = pick(promo_columns, "PRODUCT_ID", "product_id")
        promo_store = pick(promo_columns, "STORE_ID", "store_id")
        promo_week = pick(promo_columns, "WEEK_NO", "week")
        display = pick(promo_columns, "display", "display_location")
        mailer = pick(promo_columns, "mailer", "mailer_location")
        conn.execute(
            f"""
            CREATE VIEW retail_promotions AS
            SELECT
                CAST({promo_product} AS INTEGER) AS product_id,
                CAST({promo_store} AS INTEGER) AS store_id,
                CAST({promo_week} AS INTEGER) AS week_no,
                CAST({display} AS VARCHAR) AS display_location,
                CAST({mailer} AS VARCHAR) AS mailer_location
            FROM source_promotions
            """
        )
        manifest_path = root / "completejourney-manifest.json"
        metadata: dict[str, Any] = {"source": "complete-journey"}
        if manifest_path.exists():
            parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
            metadata.update(
                {
                    "source_repo": parsed.get("source_repo"),
                    "source_commit": parsed.get("source_commit"),
                    "license": parsed.get("source_license"),
                    "manifest": str(manifest_path),
                }
            )
        return cls(conn, label=f"complete-journey:{root.name}", metadata=metadata)

    def _query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        cursor = self._conn.cursor().execute(sql, list(params))
        return _records(cursor)

    def status(self) -> dict[str, Any]:
        counts = {}
        for table in ("retail_transactions", "retail_products", "retail_promotions"):
            value = self._query(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"]
            counts[table] = int(value)
        bounds = self._query(
            "SELECT MIN(week_no) AS min_week, MAX(week_no) AS max_week FROM retail_transactions"
        )[0]
        return {"label": self.label, "counts": counts, "source": self.metadata, **bounds}

    def week_bounds(self) -> tuple[list[int], list[int]]:
        row = self._query(
            "SELECT MIN(week_no) AS min_week, MAX(week_no) AS max_week FROM retail_transactions"
        )[0]
        max_week = int(row["max_week"])
        min_week = int(row["min_week"])
        current_start = max(min_week, max_week - 1)
        current = list(range(current_start, max_week + 1))
        previous_end = current_start - 1
        previous_start = max(min_week, previous_end - len(current) + 1)
        previous = list(range(previous_start, previous_end + 1))
        if not previous:
            previous = current
        return current, previous

    @staticmethod
    def _in_clause(values: list[int]) -> tuple[str, list[int]]:
        if not values:
            raise ValueError("week list must not be empty")
        return ", ".join("?" for _ in values), values

    def overview(self, current: list[int], previous: list[int]) -> dict[str, Any]:
        cur_marks, cur_params = self._in_clause(current)
        prev_marks, prev_params = self._in_clause(previous)
        sql = f"""
            WITH cur AS (
                SELECT
                    SUM(sales_value) AS sales,
                    SUM(quantity) AS units,
                    COUNT(DISTINCT basket_id) AS baskets,
                    COUNT(DISTINCT household_key) AS households,
                    SUM(ABS(retail_disc) + ABS(coupon_disc) + ABS(coupon_match_disc)) AS discount
                FROM retail_transactions WHERE week_no IN ({cur_marks})
            ),
            prev AS (
                SELECT
                    SUM(sales_value) AS sales,
                    SUM(quantity) AS units,
                    COUNT(DISTINCT basket_id) AS baskets,
                    COUNT(DISTINCT household_key) AS households,
                    SUM(ABS(retail_disc) + ABS(coupon_disc) + ABS(coupon_match_disc)) AS discount
                FROM retail_transactions WHERE week_no IN ({prev_marks})
            )
            SELECT
                cur.sales AS current_sales,
                prev.sales AS previous_sales,
                cur.units AS current_units,
                prev.units AS previous_units,
                cur.baskets AS current_baskets,
                prev.baskets AS previous_baskets,
                cur.households AS current_households,
                cur.discount AS current_discount
            FROM cur, prev
        """
        row = self._query(sql, [*cur_params, *prev_params])[0]

        def change(curr: float, prev: float) -> float:
            return ((curr - prev) / prev * 100.0) if prev else 0.0

        current_sales = float(row["current_sales"] or 0.0)
        previous_sales = float(row["previous_sales"] or 0.0)
        current_units = float(row["current_units"] or 0.0)
        previous_units = float(row["previous_units"] or 0.0)
        current_baskets = int(row["current_baskets"] or 0)
        previous_baskets = int(row["previous_baskets"] or 0)
        return {
            **row,
            "sales_change_pct": change(current_sales, previous_sales),
            "units_change_pct": change(current_units, previous_units),
            "basket_change_pct": change(current_baskets, previous_baskets),
            "avg_basket_value": current_sales / current_baskets if current_baskets else 0.0,
            "discount_rate": float(row["current_discount"] or 0.0) / current_sales if current_sales else 0.0,
        }

    def contribution(
        self,
        dimension: str,
        current: list[int],
        previous: list[int],
        *,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        if dimension == "store":
            select_dim = "CAST(t.store_id AS VARCHAR)"
            join = ""
        elif dimension in {"department", "commodity", "brand", "product"}:
            join = "JOIN retail_products p ON p.product_id = t.product_id"
            mapping = {
                "department": "p.department",
                "commodity": "p.commodity",
                "brand": "p.brand",
                "product": "CAST(t.product_id AS VARCHAR)",
            }
            select_dim = mapping[dimension]
        else:
            raise ValueError(f"unsupported contribution dimension: {dimension}")

        cur_marks, cur_params = self._in_clause(current)
        prev_marks, prev_params = self._in_clause(previous)
        sql = f"""
            WITH cur AS (
                SELECT {select_dim} AS segment, SUM(t.sales_value) AS value
                FROM retail_transactions t {join}
                WHERE t.week_no IN ({cur_marks})
                GROUP BY 1
            ),
            prev AS (
                SELECT {select_dim} AS segment, SUM(t.sales_value) AS value
                FROM retail_transactions t {join}
                WHERE t.week_no IN ({prev_marks})
                GROUP BY 1
            )
            SELECT
                COALESCE(cur.segment, prev.segment) AS segment,
                COALESCE(cur.value, 0) AS current_value,
                COALESCE(prev.value, 0) AS previous_value,
                COALESCE(cur.value, 0) - COALESCE(prev.value, 0) AS delta
            FROM cur FULL OUTER JOIN prev USING(segment)
            ORDER BY ABS(delta) DESC
            LIMIT {int(limit)}
        """
        rows = self._query(sql, [*cur_params, *prev_params])
        total_delta = sum(float(row["delta"]) for row in rows)
        for row in rows:
            delta = float(row["delta"])
            row["share_of_listed_delta"] = abs(delta) / sum(abs(float(r["delta"])) for r in rows) if rows else 0.0
            row["direction"] = "up" if delta > 0 else "down" if delta < 0 else "flat"
            row["total_listed_delta"] = total_delta
        return rows

    def cross_dimension_scan(
        self,
        current: list[int],
        previous: list[int],
        *,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Scan store × commodity space for the largest business movements."""
        cur_marks, cur_params = self._in_clause(current)
        prev_marks, prev_params = self._in_clause(previous)
        return self._query(
            f"""
            WITH cur AS (
                SELECT
                    t.store_id,
                    p.commodity,
                    SUM(t.sales_value) AS sales,
                    SUM(t.quantity) AS units
                FROM retail_transactions t
                JOIN retail_products p ON p.product_id = t.product_id
                WHERE t.week_no IN ({cur_marks})
                GROUP BY 1, 2
            ),
            prev AS (
                SELECT
                    t.store_id,
                    p.commodity,
                    SUM(t.sales_value) AS sales,
                    SUM(t.quantity) AS units
                FROM retail_transactions t
                JOIN retail_products p ON p.product_id = t.product_id
                WHERE t.week_no IN ({prev_marks})
                GROUP BY 1, 2
            )
            SELECT
                COALESCE(cur.store_id, prev.store_id) AS store_id,
                COALESCE(cur.commodity, prev.commodity) AS commodity,
                COALESCE(cur.sales, 0) AS current_sales,
                COALESCE(prev.sales, 0) AS previous_sales,
                COALESCE(cur.units, 0) AS current_units,
                COALESCE(prev.units, 0) AS previous_units,
                COALESCE(cur.sales, 0) - COALESCE(prev.sales, 0) AS sales_delta
            FROM cur
            FULL OUTER JOIN prev USING(store_id, commodity)
            ORDER BY ABS(sales_delta) DESC
            LIMIT {int(limit)}
            """,
            [*cur_params, *prev_params],
        )

    def price_volume_decomposition(
        self,
        current: list[int],
        previous: list[int],
        *,
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Decompose revenue change into price and volume effects by commodity.

        For each commodity:
          volume_effect = (q1 - q0) * p0
          price_effect  = q1 * (p1 - p0)
        These two terms exactly reconcile p1*q1 - p0*q0 when units are nonzero.
        """
        cur_marks, cur_params = self._in_clause(current)
        prev_marks, prev_params = self._in_clause(previous)
        rows = self._query(
            f"""
            WITH cur AS (
                SELECT
                    p.commodity,
                    SUM(t.sales_value) AS sales,
                    SUM(t.quantity) AS units
                FROM retail_transactions t
                JOIN retail_products p ON p.product_id = t.product_id
                WHERE t.week_no IN ({cur_marks})
                GROUP BY 1
            ),
            prev AS (
                SELECT
                    p.commodity,
                    SUM(t.sales_value) AS sales,
                    SUM(t.quantity) AS units
                FROM retail_transactions t
                JOIN retail_products p ON p.product_id = t.product_id
                WHERE t.week_no IN ({prev_marks})
                GROUP BY 1
            )
            SELECT
                COALESCE(cur.commodity, prev.commodity) AS commodity,
                COALESCE(cur.sales, 0) AS current_sales,
                COALESCE(prev.sales, 0) AS previous_sales,
                COALESCE(cur.units, 0) AS current_units,
                COALESCE(prev.units, 0) AS previous_units
            FROM cur
            FULL OUTER JOIN prev USING(commodity)
            """,
            [*cur_params, *prev_params],
        )
        decomposed: list[dict[str, Any]] = []
        for row in rows:
            current_sales = float(row["current_sales"] or 0.0)
            previous_sales = float(row["previous_sales"] or 0.0)
            current_units = float(row["current_units"] or 0.0)
            previous_units = float(row["previous_units"] or 0.0)
            current_price = current_sales / current_units if current_units else 0.0
            previous_price = previous_sales / previous_units if previous_units else 0.0
            volume_effect = (current_units - previous_units) * previous_price
            price_effect = current_units * (current_price - previous_price)
            decomposed.append(
                {
                    **row,
                    "current_price": current_price,
                    "previous_price": previous_price,
                    "volume_effect": volume_effect,
                    "price_effect": price_effect,
                    "sales_delta": current_sales - previous_sales,
                    "reconciliation_error": (current_sales - previous_sales)
                    - volume_effect
                    - price_effect,
                }
            )
        return sorted(
            decomposed,
            key=lambda row: abs(float(row["sales_delta"])),
            reverse=True,
        )[:limit]

    def promotion_performance(self, current: list[int], *, limit: int = 12) -> list[dict[str, Any]]:
        marks, params = self._in_clause(current)
        return self._query(
            f"""
            SELECT
                COALESCE(NULLIF(TRIM(p.display_location), ''), 'UNKNOWN') AS display_location,
                COUNT(*) AS line_items,
                SUM(t.sales_value) AS sales,
                SUM(t.quantity) AS units,
                AVG(t.sales_value) AS avg_line_sales
            FROM retail_transactions t
            JOIN retail_promotions p
              ON p.product_id = t.product_id
             AND p.store_id = t.store_id
             AND p.week_no = t.week_no
            WHERE t.week_no IN ({marks})
            GROUP BY 1
            ORDER BY sales DESC
            LIMIT {int(limit)}
            """,
            params,
        )

    def basket_affinity(self, current: list[int], *, limit: int = 10) -> list[dict[str, Any]]:
        marks, params = self._in_clause(current)
        return self._query(
            f"""
            WITH pairs AS (
                SELECT
                    LEAST(a.product_id, b.product_id) AS product_a,
                    GREATEST(a.product_id, b.product_id) AS product_b,
                    COUNT(DISTINCT a.basket_id) AS basket_count
                FROM retail_transactions a
                JOIN retail_transactions b
                  ON a.basket_id = b.basket_id
                 AND a.product_id < b.product_id
                WHERE a.week_no IN ({marks})
                GROUP BY 1, 2
            )
            SELECT * FROM pairs
            ORDER BY basket_count DESC, product_a, product_b
            LIMIT {int(limit)}
            """,
            params,
        )

    def customer_segments(self, current: list[int], *, limit: int = 10) -> list[dict[str, Any]]:
        marks, params = self._in_clause(current)
        return self._query(
            f"""
            SELECT
                household_key,
                COUNT(DISTINCT basket_id) AS trips,
                SUM(sales_value) AS sales,
                SUM(quantity) AS units
            FROM retail_transactions
            WHERE week_no IN ({marks})
            GROUP BY 1
            ORDER BY sales DESC
            LIMIT {int(limit)}
            """,
            params,
        )

    def store_anomalies(self, current: list[int], *, limit: int = 10) -> list[dict[str, Any]]:
        marks, params = self._in_clause(current)
        rows = self._query(
            f"""
            SELECT store_id, week_no, SUM(sales_value) AS sales
            FROM retail_transactions
            WHERE week_no IN ({marks})
            GROUP BY 1, 2
            ORDER BY store_id, week_no
            """,
            params,
        )
        by_store: dict[int, list[float]] = {}
        for row in rows:
            by_store.setdefault(int(row["store_id"]), []).append(float(row["sales"]))
        flattened = [value for values in by_store.values() for value in values]
        if len(flattened) < 2:
            return []
        mean = fmean(flattened)
        std = pstdev(flattened) or 1.0
        scored = [
            {
                "store_id": store,
                "latest_sales": values[-1],
                "zscore": (values[-1] - mean) / std,
                "mean_all_store_weeks": mean,
            }
            for store, values in by_store.items()
        ]
        return sorted(scored, key=lambda row: abs(float(row["zscore"])), reverse=True)[:limit]
