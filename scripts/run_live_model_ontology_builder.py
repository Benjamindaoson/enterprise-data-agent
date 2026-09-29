#!/usr/bin/env python3
"""Credentialed live model-driven ontology construction on real UCI data."""

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
from eiw.ontology.model_builder import model_builder_from_env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url",
        default=os.getenv("EIW_TEST_DATABASE_URL", ""),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("artifacts/ontology-live-builder"),
    )
    parser.add_argument("--max-rows", type=int, default=10_000)
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()

    api_key = (
        os.getenv("EIW_ONTOLOGY_MODEL_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )
    if not api_key:
        if args.require_live:
            print("Live ontology model credential is required.")
            return 2
        print(json.dumps({"status": "SKIPPED", "reason": "credential_not_configured"}))
        return 0
    if not args.database_url:
        raise SystemExit("EIW_TEST_DATABASE_URL or --database-url is required")

    source = download(
        ONLINE_RETAIL_URL,
        args.root / "raw" / "online-retail.zip",
    )
    loaded = load_online_retail_sample_into_postgres(
        source,
        database_url=args.database_url,
        max_rows=args.max_rows,
    )
    connector = blind_connector(args.database_url)
    builder = model_builder_from_env(connector)
    state, usage = builder.build(
        ontology_id="live-online-retail",
        version="1.0.0-model",
        workload=list(BlindOnboardingBenchmark.ADAPTATION_WORKLOAD),
    )

    semantic_ids = {
        term.canonical_id
        for term in state.terms.values()
        if term.canonical_id
    }
    required = {"revenue", "country"}
    missing = sorted(required - semantic_ids)
    result = {
        "status": "PASS" if not missing else "FAIL",
        "builder": state.metadata.get("builder"),
        "ontology_id": state.ontology_id,
        "version": state.version,
        "content_hash": state.content_hash,
        "source": "UCI Online Retail",
        "loaded_rows": loaded["rows"],
        "gold_semantics_exposed_to_builder": False,
        "semantic_ids": sorted(semantic_ids),
        "missing_required_semantics": missing,
        "usage": {
            "provider": usage.provider,
            "model": usage.model,
            "latency_ms": usage.latency_ms,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "estimated_cost_usd": usage.estimated_cost_usd,
        },
    }
    args.root.mkdir(parents=True, exist_ok=True)
    (args.root / "live-model-builder.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n"
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if not missing else 3


if __name__ == "__main__":
    raise SystemExit(main())
