#!/usr/bin/env python3
"""Measure BA Agent latency on a local Complete Journey dataset.

This script reports only locally measured values. It does not download data and
does not fabricate scale claims.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import fmean, median
from time import perf_counter

from eiw.retail.data import RetailDataEngine
from eiw.retail.models import RetailAnalysisRequest
from eiw.retail.runtime import RetailBARuntime


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()

    runtime = RetailBARuntime(RetailDataEngine.from_complete_journey(args.data_dir))
    request = RetailAnalysisRequest(
        question="Analyze recent business performance, identify the biggest drivers and recommend next actions."
    )

    runtime.analyze(request)
    latencies: list[float] = []
    started = perf_counter()

    def once() -> float:
        t0 = perf_counter()
        runtime.analyze(request)
        return (perf_counter() - t0) * 1000.0

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = [pool.submit(once) for _ in range(args.requests)]
        for future in as_completed(futures):
            latencies.append(future.result())

    wall_seconds = perf_counter() - started
    status = runtime.data.status()
    result = {
        "dataset": status,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "mean_ms": fmean(latencies),
        "median_ms": median(latencies),
        "p95_ms": percentile(latencies, 0.95),
        "throughput_requests_per_second": args.requests / wall_seconds if wall_seconds else 0.0,
    }
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
