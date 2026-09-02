"""Validate a built Iowa snapshot and publish only measured READY metadata."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import duckdb


def sql_path(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", default="iowa_liquor_snapshot_2026_07_v1")
    parser.add_argument("--curated-root", type=Path, default=Path("data/curated"))
    args = parser.parse_args()
    folder = args.curated_root / args.snapshot_id
    manifest_path = folder / "manifest.json"
    fact_path = folder / "fact_liquor_order_line.parquet"
    if not manifest_path.exists() or not fact_path.exists() or fact_path.stat().st_size == 0:
        raise SystemExit(f"snapshot is not built: {folder}")
    manifest = json.loads(manifest_path.read_text())
    con = duckdb.connect()
    con.execute(f"CREATE VIEW fact AS SELECT * FROM read_parquet({sql_path(fact_path)})")
    columns = {row[0] for row in con.execute("DESCRIBE fact").fetchall()}
    required = {"source_record_id", "order_date", "line_wholesale_sales_amount", "bottles_ordered", "state_cost_per_bottle"}
    profile = con.execute(
        """SELECT count(*), count(DISTINCT source_record_id), min(order_date), max(order_date),
           count(*) FILTER (WHERE order_date < DATE '2025-07-01' AND state_cost_per_bottle IS NOT NULL),
           count(*) FILTER (WHERE order_date >= DATE '2025-07-01' AND state_cost_per_bottle IS NULL),
           sum(line_wholesale_sales_amount), sum(bottles_ordered) FROM fact"""
    ).fetchone()
    checks = {
        "required_fields": required.issubset(columns),
        "source_record_id_unique": profile[0] == profile[1],
        "date_coverage": profile[2] == date(2024, 1, 1) and profile[3] == date(2026, 7, 31),
        "cost_boundary": profile[4] == 0,
        "in_window_cost_complete": profile[5] == 0,
        "manifest_row_count": profile[0] == manifest.get("row_count"),
        "manifest_sales": str(profile[6]) == manifest.get("wholesale_sales_amount"),
    }
    status = "READY" if all(checks.values()) else "REJECTED"
    manifest["status"] = status
    manifest["validation"] = {key: "PASSED" if value else "FAILED" for key, value in checks.items()}
    manifest["validated_at"] = __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"snapshot_id": args.snapshot_id, "status": status, "checks": checks, "row_count": profile[0], "sales": str(profile[6]), "bottles": str(profile[7])}, indent=2))
    if status != "READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
