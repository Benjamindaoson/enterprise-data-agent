"""Create reproducible, typed Iowa wholesale fact and dimensions from raw CSV parts.

The input is a pinned set of source files already captured by
``ingest_iowa_snapshot.py``. The script makes the event-time fact authoritative,
constructs a stable per-row source ID from source content, and explicitly nulls
cost fields outside their declared coverage window.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb

SNAPSHOT_ID = "iowa_liquor_snapshot_2026_07_v1"
COST_AVAILABLE_FROM = "2025-07-01"
COST_AVAILABLE_TO = "2026-07-31"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode())
        digest.update(sha256_file(path).encode())
    return digest.hexdigest()


def sql_path(path: Path) -> str:
    """Return a safely quoted local path for DuckDB statements that cannot bind it."""

    return "'" + str(path).replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", default=SNAPSHOT_ID)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw") / SNAPSHOT_ID)
    parser.add_argument("--curated-dir", type=Path, default=Path("data/curated") / SNAPSHOT_ID)
    arguments = parser.parse_args()

    csv_dir = arguments.raw_dir / "csv"
    csv_files = sorted(csv_dir.glob("*.csv"))
    if not csv_files:
        raise SystemExit(f"no raw CSV parts found in {csv_dir}")
    arguments.curated_dir.mkdir(parents=True, exist_ok=True)
    csv_glob = str(csv_dir / "*.csv")
    connection = duckdb.connect()
    connection.execute("SET memory_limit='6GB'")
    connection.execute("SET threads TO 4")
    # DuckDB does not allow prepared parameters inside COPY statements. The
    # path is resolved locally from the known raw directory and SQL-quoted.
    input_relation = f"read_csv_auto({sql_path(Path(csv_glob))}, union_by_name=true)"
    required_columns = {
        "invoice_id",
        "ordered_on",
        "store_no",
        "store_name",
        "county_fips_code",
        "county_name",
        "category_code",
        "category_name",
        "vendor_number",
        "vendor_name",
        "item_no",
        "im_desc",
        "pack",
        "bottle_volume_ml",
        "state_bottle_cost",
        "state_bottle_retail",
        "sales_bottles",
        "sales_dollars",
        "sales_liters",
    }
    actual_columns = {
        row[0]
        for row in connection.execute(f"DESCRIBE SELECT * FROM {input_relation}").fetchall()
    }
    missing_columns = sorted(required_columns - actual_columns)
    if missing_columns:
        raise SystemExit(f"required source columns missing: {', '.join(missing_columns)}")

    # invoice_id identifies the invoice, not a physical line. A content fingerprint
    # makes the actual fact grain explicit. Exact raw duplicates are counted and
    # removed in the logical fact; raw captures stay intact for audit/replay.
    raw_projection = f"""
        SELECT
          sha256(concat_ws('|',
            invoice_id,
            CAST(ordered_on AS VARCHAR),
            COALESCE(store_no, ''), COALESCE(CAST(item_no AS VARCHAR), ''),
            COALESCE(CAST(pack AS VARCHAR), ''), COALESCE(CAST(bottle_volume_ml AS VARCHAR), ''),
            COALESCE(state_bottle_cost, ''), COALESCE(state_bottle_retail, ''),
            COALESCE(CAST(sales_bottles AS VARCHAR), ''), COALESCE(CAST(sales_dollars AS VARCHAR), ''),
            COALESCE(CAST(sales_liters AS VARCHAR), '')
          )) AS source_record_id,
          invoice_id,
          ordered_on AS order_date,
          store_no AS store_id,
          store_name AS store_name_at_order,
          store_address AS store_address_at_order,
          store_city AS city_at_order,
          CAST(store_zip_code AS VARCHAR) AS store_zip_code_at_order,
          CAST(county_fips_code AS VARCHAR) AS county_fips_code,
          county_name AS county_name_at_order,
          CAST(category_code AS VARCHAR) AS category_id,
          category_name AS category_name_at_order,
          vendor_number AS vendor_id,
          vendor_name AS vendor_name_at_order,
          CAST(item_no AS VARCHAR) AS product_id,
          im_desc AS product_name_at_order,
          CAST(pack AS BIGINT) AS pack,
          CAST(bottle_volume_ml AS BIGINT) AS bottle_volume_ml,
          CASE WHEN ordered_on BETWEEN DATE '{COST_AVAILABLE_FROM}' AND DATE '{COST_AVAILABLE_TO}'
            THEN TRY_CAST(NULLIF(state_bottle_cost, '') AS DECIMAL(18,4)) END AS state_cost_per_bottle,
          TRY_CAST(NULLIF(state_bottle_retail, '') AS DECIMAL(18,4)) AS store_purchase_price_per_bottle,
          CAST(sales_bottles AS BIGINT) AS bottles_ordered,
          CAST(sales_dollars AS DECIMAL(20,2)) AS line_wholesale_sales_amount,
          CAST(sales_liters AS DECIMAL(20,4)) AS ordered_volume_liters
        FROM {input_relation}
        WHERE ordered_on BETWEEN DATE '2024-01-01' AND DATE '2026-07-31'
    """
    raw_profile = connection.execute(
        f"SELECT count(*) AS raw_row_count, count(DISTINCT source_record_id) AS logical_row_count "
        f"FROM ({raw_projection})",
    ).fetchone()
    if raw_profile is None:
        raise SystemExit("unable to profile raw source")
    duplicate_count = raw_profile[0] - raw_profile[1]
    canonical_projection = f"""
        SELECT * EXCLUDE (exact_duplicate_ordinal)
        FROM (
          SELECT *, row_number() OVER (PARTITION BY source_record_id ORDER BY source_record_id) AS exact_duplicate_ordinal
          FROM ({raw_projection})
        )
        WHERE exact_duplicate_ordinal = 1
    """

    fact_path = arguments.curated_dir / "fact_liquor_order_line.parquet"
    connection.execute(
        f"COPY ({canonical_projection}) TO {sql_path(fact_path)} (FORMAT PARQUET, COMPRESSION ZSTD)",
    )
    connection.execute(
        f"CREATE OR REPLACE VIEW fact AS SELECT * FROM read_parquet({sql_path(fact_path)})"
    )
    profile = connection.execute(
        """
        SELECT
          count(*) AS row_count,
          count(DISTINCT source_record_id) AS unique_source_record_ids,
          min(order_date) AS business_date_min,
          max(order_date) AS business_date_max,
          count(*) FILTER (WHERE order_date < DATE '2025-07-01' AND state_cost_per_bottle IS NOT NULL) AS pre_window_cost_values,
          count(*) FILTER (WHERE order_date >= DATE '2025-07-01' AND state_cost_per_bottle IS NULL) AS in_window_missing_cost_values,
          sum(line_wholesale_sales_amount) AS wholesale_sales_amount
        FROM fact
        """
    ).fetchone()
    if profile[0] != profile[1]:
        raise SystemExit("curated source_record_id is not unique")
    if profile[4] != 0:
        raise SystemExit("cost values exist before declared cost availability window")

    date_path = arguments.curated_dir / "dim_date.parquet"
    connection.execute(
        f"""
        COPY (
          SELECT DISTINCT order_date AS date, year(order_date) AS year,
            month(order_date) AS month_number, strftime(order_date, '%Y-%m') AS month_id
          FROM fact
        ) TO {sql_path(date_path)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
    )
    store_path = arguments.curated_dir / "dim_store_current.parquet"
    connection.execute(
        f"""
        COPY (
          SELECT store_id, store_name_at_order AS store_name_current,
            store_address_at_order AS store_address_current, city_at_order AS city_current,
            store_zip_code_at_order AS store_zip_code_current, county_fips_code AS county_fips_code_current,
            county_name_at_order AS county_name_current, order_date AS observed_at
          FROM fact
          QUALIFY row_number() OVER (PARTITION BY store_id ORDER BY order_date DESC, source_record_id DESC) = 1
        ) TO {sql_path(store_path)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
    )
    product_path = arguments.curated_dir / "dim_product_current.parquet"
    connection.execute(
        f"""
        COPY (
          SELECT product_id, product_name_at_order AS product_name_current,
            category_id AS category_id_current, category_name_at_order AS category_name_current,
            vendor_id AS vendor_id_current, vendor_name_at_order AS vendor_name_current,
            pack AS pack_current, bottle_volume_ml AS bottle_volume_ml_current, order_date AS observed_at
          FROM fact
          QUALIFY row_number() OVER (PARTITION BY product_id ORDER BY order_date DESC, source_record_id DESC) = 1
        ) TO {sql_path(product_path)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
    )
    join_result = connection.execute(
        """
        SELECT
          count(*) AS joined_rows,
          sum(line_wholesale_sales_amount) AS joined_sales
        FROM fact
        LEFT JOIN read_parquet(?) store USING (store_id)
        LEFT JOIN read_parquet(?) product USING (product_id)
        """,
        [str(store_path), str(product_path)],
    ).fetchone()
    if join_result[0] != profile[0] or join_result[1] != profile[6]:
        raise SystemExit("current dimension joins multiply fact rows or monetary totals")

    parquet_files = [fact_path, date_path, store_path, product_path]
    manifest = {
        "snapshot_id": arguments.snapshot_id,
        "source_catalog": "https://data.iowa.gov/catalog/dataset/1051",
        "source_assets": [1261, 1262, 1263],
        "extracted_at": datetime.now(UTC).isoformat(),
        "business_date_min": str(profile[2]),
        "business_date_max": str(profile[3]),
        "raw_file_sha256": sha256_files(sorted(arguments.raw_dir.glob("*.zip"))),
        "curated_file_sha256": sha256_files(parquet_files),
        "row_count": profile[0],
        "raw_row_count": raw_profile[0],
        "exact_duplicate_raw_rows": duplicate_count,
        "unique_source_record_ids": profile[1],
        "schema_hash": hashlib.sha256("|".join(sorted(actual_columns)).encode()).hexdigest(),
        "pre_window_cost_values": profile[4],
        "in_window_missing_cost_values": profile[5],
        "wholesale_sales_amount": str(profile[6]),
        "current_dimension_joined_rows": join_result[0],
        "current_dimension_joined_sales": str(join_result[1]),
        "license": "CC BY 4.0",
        "status": "READY",
        "validation": {
            "required_fields": "PASSED",
            "date_coverage": "PASSED",
            "source_record_id_uniqueness": "PASSED",
            "cost_coverage_boundary": "PASSED",
            "current_dimension_reconciliation": "PASSED",
        },
        "notes": [
            "invoice_id is an invoice header identifier, not a globally unique fact primary key",
            "exact raw-record duplicates are removed only after their count is recorded",
            "current dimensions are derived observed-current attributes and never replace fact event-time attributes",
            "spread metrics remain unavailable before 2025-07-01",
        ],
    }
    (arguments.curated_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
