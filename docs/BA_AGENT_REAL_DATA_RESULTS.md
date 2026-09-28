# Retail BA Agent real-data baseline

This document records a reproducible measured baseline for the Retail BA Agent.
It is intentionally scoped to the exact public dataset, benchmark suite and CI
environment below. It is not presented as an external SoTA result.

## Dataset

Source distribution:

- repository: `bradleyboehmke/completejourney`
- pinned source commit: `5b5d06192b9856edd04e4d405787af2f2e4a1fef`
- declared source license: **CC0**
- materialization: RDS/RDA -> zstd Parquet
- provenance: source URL + source SHA-256 + Parquet SHA-256 + rows + columns in
  `completejourney-manifest.json`

Measured normalized relations:

| Relation | Rows |
| --- | ---: |
| transactions | 1,469,307 |
| promotions | 20,940,529 |
| products | 92,331 |
| demographics | 801 |
| campaigns | 6,589 |
| campaign descriptions | 27 |
| coupons | 116,204 |
| coupon redemptions | 2,102 |

The ingestion command is:

```bash
python -m pip install -e '.[dev,retail-data]'
python scripts/fetch_completejourney_cc0.py data/retail
```

The downloader is commit-pinned and manifest-driven. When the same valid
Parquet materialization is restored from cache it is reused rather than
downloaded again.

## RetailAnalystBench-v1

Measured workflow run:

- GitHub Actions run: `36414459712`
- evidence commit: `fa064b1711cb1057bec6d0c766038ade9ee386ec`
- benchmark artifact: `10965843223`
- gold method: **independent_readonly_sql**
- cases: **10**

Aggregate result:

| Metric | Result |
| --- | ---: |
| Driver Recall@K | **1.000** |
| Semantic Coverage | **1.000** |
| Numeric Accuracy | **1.000** |
| Report Completeness | **1.000** |
| Action Coverage | **1.000** |
| Mean time to first insight | **287.70 ms** |
| Mean end-to-end latency | **301.04 ms** |
| End-to-end P95 | **309.17 ms** |

The ten cases cover:

1. KPI summary;
2. sales-decline diagnosis;
3. store drivers;
4. product/category drivers;
5. store x commodity cross-dimensional investigation;
6. price-volume decomposition;
7. promotion / merchandising analysis;
8. customer / basket opportunities;
9. customer income-segment analysis;
10. executive business review.

Numeric gold is calculated with direct SQL over the normalized views, not by
calling the same typed analytical methods used by the Agent workers. Benchmark
output also records expected/matched driver terms and any missing semantic
items per case so failures can be mined rather than hidden behind one score.

## Latency smoke

The same workflow ran three end-to-end requests with concurrency=1:

| Metric | Result |
| --- | ---: |
| Requests | 3 |
| Concurrency | 1 |
| Mean | **301.89 ms** |
| Median | **300.39 ms** |
| P95 | **400.28 ms** |
| Throughput | **3.31 requests/s** |

This is a small GitHub-hosted CI smoke measurement. It is useful as a
regression baseline, not as a production throughput claim. Larger local/hosted
runs should report machine configuration, request count and concurrency before
being used in resume claims.

## Rolling-window robustness

`RetailAnalystBench-Rolling-v1` expands the fixed latest-window suite into 30 cases across 5 historical week windows.

| Rolling metric | Result |
| --- | ---: |
| Cases | **30** |
| Historical windows | **5** |
| Driver Recall@K | **1.000** |
| Semantic Coverage | **1.000** |
| Numeric Accuracy | **1.000** |
| Report Completeness | **1.000** |
| Action Coverage | **1.000** |
| Mean time to first insight | **312.08 ms** |
| Mean end-to-end latency | **325.70 ms** |
| End-to-end P95 | **377.21 ms** |

This is an internal robustness suite over multiple time windows, not an external benchmark claim.

## Harness ablation

The same workflow also runs `RetailHarnessAblation-v1`. It reuses the exact
same typed workstream outputs and changes only harness-level selection and
execution behavior.

| Ablation metric | Result |
| --- | ---: |
| Intrinsic-score Driver Recall@K | **0.900** |
| Query-aware Driver Recall@K | **1.000** |
| Gain | **+10.0 pp** |
| Cases where re-plan added specialists | **8 / 10** |
| Mean initial workstreams | **3.4** |
| Mean final workstreams | **4.6** |
| Sequential specialist wall time | **356.73 ms** |
| Parallel specialist wall time | **270.83 ms** |
| Parallel wall-clock speedup | **1.32×** |

The purpose of this ablation is narrower than an external system comparison:
it isolates the contribution of query-aware ranking, dynamic re-planning and
parallel specialist execution while keeping the underlying analytical
operators/data fixed.

## Browser product proof

The same pinned workflow starts the real-data FastAPI application, opens `/ba`
with Playwright Chromium and executes the product end to end. Artifact
`10957970871` contains:

- `ba-agent-before-run.png`;
- `ba-agent-real-data.png`;
- `ba-agent-real-data.webm`;
- `ba-agent-trace.zip`;
- `ba-agent-executive-report.html`;
- `ba-agent-executive-report.pdf`;
- `demo-proof.txt`;
- `retail-harness-ablation.json`;\n- the benchmark/scale JSON and data manifest.

The captured UI reports the exact dataset provenance
`complete-journey:retail · 1,469,307 transactions · CC0 · 5b5d061`.
The generated PDF was rendered in CI from the same analytical response.

## Development adversarial gate

The development partition contains **168 cases / 14 categories** and is the
place where guard/runtime behavior may be iterated. The verified core CI run
passed **164 / 168 (97.62%)** cases. Security resistance and malformed-model
fallback recovery were both **1.000**. The four misses are retained in the
missing-data family rather than rewritten after the result.

## Adversarial frozen holdout

The 9.5 hardening pass adds `RetailAdversarialBench-v1` with 210 total cases across 14 failure families. The development partition contains 168 deterministic cases; a separate **42-case frozen holdout** is stored as checksum-pinned JSONL and is not intended for tuning.

Pinned real-data verification:

- GitHub Actions run: `36437826206`
- artifact: `10976531496`
- dataset: pinned CC0 Complete Journey
- frozen cases: **42**
- categories: **14**
- pass rate: **1.000**
- security resistance: **1.000**
- malformed-model fallback recovery: **1.000**

The frozen suite covers paraphrase, ambiguity, impossible requests, missing data, unsupported causal requests, conflicting dimensions, unavailable time ranges, unseen combinations, schema distractors, adversarial prompts, prompt injection, irrelevant requests, multi-turn follow-up and malformed model decisions.

The 1.000 result is reported only as an internal contract/robustness result. It is not an external benchmark or evidence that arbitrary enterprise questions are solved perfectly.

## Regression gate

`scripts/run_retail_benchmark.py --assert-smoke` currently requires:

- Driver Recall@K >= 0.90
- Semantic Coverage >= 0.95
- Numeric Accuracy = 1.00
- Report Completeness = 1.00
- Action Coverage = 1.00

Both deterministic CI and the public real-data workflow execute the gate. The core workflow requires the 168-case development partition to clear its release threshold and the immutable 42-case frozen partition to clear its own threshold; the real-data workflow independently gates the frozen 42-case holdout.

## Claim discipline

The retail dataset is observational. Promotion, display, campaign and coupon
comparisons are described as **associations / observed funnels** unless a
matched or experimental design supports causal language.
