#!/usr/bin/env python3
"""Run one Retail BA Agent rollout under an Agent Lightning controller."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from eiw.training.agent_lightning_agent import execute_retail_rollout


def _configure_case(path: Path | None) -> None:
    if os.getenv("EIW_AGL_CASE_JSON", "").strip():
        return
    if path is None:
        raise RuntimeError("EIW_AGL_CASE_JSON or --case-json is required")
    os.environ["EIW_AGL_CASE_JSON"] = path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-json", type=Path)
    args = parser.parse_args()
    _configure_case(args.case_json)

    result = execute_retail_rollout()
    print(
        json.dumps(
            {
                **result,
                "reward": round(float(result["reward"]), 6),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
