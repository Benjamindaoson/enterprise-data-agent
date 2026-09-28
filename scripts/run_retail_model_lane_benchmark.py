from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.retail.data import RetailDataEngine
from eiw.retail.model_lane_benchmark import ModelProviderSpec, RetailModelLaneBenchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument(
        "--providers",
        default="qwen,gpt,claude",
        help="Comma-separated provider environment prefixes.",
    )
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    names = [name.strip() for name in args.providers.split(",") if name.strip()]
    providers = [
        spec
        for name in names
        if (spec := ModelProviderSpec.from_env(name)) is not None
    ]
    if args.require_live and len(providers) < 3:
        missing = [name for name in names if ModelProviderSpec.from_env(name) is None]
        raise SystemExit(
            "live benchmark requires three configured providers; missing: "
            + ", ".join(missing)
        )

    data = (
        RetailDataEngine.from_complete_journey(args.data_dir)
        if args.data_dir
        else RetailDataEngine.demo()
    )
    result = RetailModelLaneBenchmark(data).run(providers)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
