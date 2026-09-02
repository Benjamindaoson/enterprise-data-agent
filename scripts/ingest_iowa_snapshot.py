"""Fetch an explicitly pinned Iowa source file and write its immutable manifest.

Usage deliberately requires the resolved source URL and snapshot ID. The public
catalog's mutable "latest" view is never used as a Golden Evaluation input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlretrieve

import duckdb
import yaml

REQUIRED_FIELDS = set(
    yaml.safe_load(Path("data/source-contracts/iowa_liquor_sales.yaml").read_text())["source"][
        "required_fields"
    ]
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument(
        "--source-updated-at", required=True, help="ISO 8601 timestamp from official catalog"
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--input-file", type=Path, help="Use a manually downloaded immutable source file"
    )
    arguments = parser.parse_args()

    output_dir = arguments.output_dir / arguments.snapshot_id
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "liquor_sales.csv"
    if arguments.input_file:
        raw_path.write_bytes(arguments.input_file.read_bytes())
    else:
        urlretrieve(arguments.source_url, raw_path)  # noqa: S310 - explicit public source parameter

    connection = duckdb.connect()
    columns = {
        row[0]
        for row in connection.execute(
            "DESCRIBE SELECT * FROM read_csv_auto(?, header=true)", [str(raw_path)]
        ).fetchall()
    }
    missing = sorted(REQUIRED_FIELDS - columns)
    if missing:
        raise SystemExit(f"source contract failure; missing fields: {', '.join(missing)}")
    profile = connection.execute(
        "SELECT count(*) AS row_count, min(ordered_on) AS min_date, max(ordered_on) AS max_date, "
        "count(*) - count(DISTINCT invoice_id) AS duplicate_invoice_ids "
        "FROM read_csv_auto(?, header=true)",
        [str(raw_path)],
    ).fetchone()
    if profile is None or profile[3] != 0:
        raise SystemExit("source contract failure; invoice_id must be unique")
    schema_hash = hashlib.sha256("|".join(sorted(columns)).encode()).hexdigest()
    manifest = {
        "snapshot_id": arguments.snapshot_id,
        "source_url": arguments.source_url,
        "extracted_at": datetime.now(UTC).isoformat(),
        "source_last_updated_at": arguments.source_updated_at,
        "business_date_min": str(profile[1]),
        "business_date_max": str(profile[2]),
        "raw_file_sha256": sha256_file(raw_path),
        "curated_file_sha256": None,
        "row_count": profile[0],
        "schema_hash": schema_hash,
        "license": "CC BY 4.0",
        "status": "RAW_CAPTURED",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
