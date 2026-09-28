"""Run BA Agent harness ablations on fixture or real retail data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from eiw.retail.ablation import RetailHarnessAblationRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.runtime import RetailBARuntime


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    configured = args.data_dir or (
        Path(os.environ["EIW_RETAIL_DATA_DIR"])
        if os.getenv("EIW_RETAIL_DATA_DIR")
        else None
    )
    data = (
        RetailDataEngine.from_complete_journey(configured)
        if configured is not None
        else RetailDataEngine.demo()
    )
    result = RetailHarnessAblationRunner(RetailBARuntime(data)).run()
    rendered = json.dumps(result, indent=2, default=str)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
