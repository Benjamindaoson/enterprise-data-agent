"""Download official public datasets and build BusinessAgentBench real-data tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.benchmark.public_data import (
    BANK_MARKETING_URL,
    ONLINE_RETAIL_URL,
    download,
    profile_bank_marketing,
    profile_online_retail,
    write_business_agent_benchmark,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("artifacts/business-benchmark"))
    parser.add_argument("--bank-only", action="store_true")
    args = parser.parse_args()

    raw = args.root / "raw"
    bank_zip = download(BANK_MARKETING_URL, raw / "bank-marketing.zip")
    bank_profile = profile_bank_marketing(bank_zip)

    retail_profile = None
    if not args.bank_only:
        retail_zip = download(ONLINE_RETAIL_URL, raw / "online-retail.zip")
        retail_profile = profile_online_retail(retail_zip)

    payload = write_business_agent_benchmark(
        args.root / "business-agent-bench-real.json",
        bank_profile=bank_profile,
        retail_profile=retail_profile,
    )
    print(
        json.dumps(
            {
                "benchmark": payload["benchmark"],
                "task_count": len(payload["tasks"]),
                "sources": [source["dataset_id"] for source in payload["sources"]],
                "bank_rows": bank_profile["row_count"],
                "retail_rows": retail_profile["row_count"] if retail_profile else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
