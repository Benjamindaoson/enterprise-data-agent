#!/usr/bin/env python3
"""Convert common Complete Journey CSV files into analysis-ready Parquet.

The script never downloads restricted or third-party data. Point it at a local
copy obtained under the dataset's terms.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def quote(value: Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    raw = args.raw_dir.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    mapping = {
        "transaction_data.csv": "transaction_data.parquet",
        "product.csv": "product.parquet",
        "causal_data.csv": "causal_data.parquet",
    }
    conn = duckdb.connect(":memory:")
    for source_name, target_name in mapping.items():
        source = raw / source_name
        if not source.exists():
            raise FileNotFoundError(source)
        target = output / target_name
        conn.execute(
            f"COPY (SELECT * FROM read_csv_auto({quote(source)}, header=true)) "
            f"TO {quote(target)} (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        print(f"{source_name} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
