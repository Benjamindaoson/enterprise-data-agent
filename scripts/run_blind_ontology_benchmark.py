#!/usr/bin/env python3
"""Run blind semantic onboarding + four-lane ablation on real UCI retail data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from eiw.benchmark.public_data import ONLINE_RETAIL_URL, download
from eiw.ontology.benchmark import (
    BlindOnboardingBenchmark,
    blind_connector,
    load_online_retail_sample_into_postgres,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url",
        default=os.getenv("EIW_TEST_DATABASE_URL", ""),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("artifacts/ontology-blind-benchmark"),
    )
    parser.add_argument("--max-rows", type=int, default=25_000)
    parser.add_argument("--assert-gate", action="store_true")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("EIW_TEST_DATABASE_URL or --database-url is required")

    raw = args.root / "raw"
    source = download(ONLINE_RETAIL_URL, raw / "online-retail.zip")
    loaded = load_online_retail_sample_into_postgres(
        source,
        database_url=args.database_url,
        max_rows=args.max_rows,
    )
    connector = blind_connector(args.database_url)
    result = BlindOnboardingBenchmark(
        connector,
        schema_name=loaded["schema"],
        table_name=loaded["table"],
    ).run()
    result["dataset"]["loaded_rows"] = loaded["rows"]
    result["dataset"]["source_url"] = ONLINE_RETAIL_URL
    result["dataset"]["gold_semantics_exposed_to_builder"] = False

    args.root.mkdir(parents=True, exist_ok=True)
    output = args.root / "blind-ontology-benchmark.json"
    output.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps(result, indent=2, default=str))

    if args.assert_gate:
        failed = [
            name
            for name, passed in result["assertions"].items()
            if not passed
        ]
        if failed:
            print("FAILED ASSERTIONS:", ", ".join(failed))
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
