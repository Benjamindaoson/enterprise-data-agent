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

- GitHub Actions run: `36390530467`
- source commit: `42c95622e3ef7302b4b11cbd6327f70ac585f85b`
- benchmark artifact: `10955597771`
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
| Mean time to first insight | **356.39 ms** |
| Mean end-to-end latency | **373.29 ms** |
| End-to-end P95 | **400.55 ms** |

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
| Mean | **392.25 ms** |
| Median | **395.18 ms** |
| P95 | **398.85 ms** |
| Throughput | **2.55 requests/s** |

This is a small GitHub-hosted CI smoke measurement. It is useful as a
regression baseline, not as a production throughput claim. Larger local/hosted
runs should report machine configuration, request count and concurrency before
being used in resume claims.

## Regression gate

`scripts/run_retail_benchmark.py --assert-smoke` currently requires:

- Driver Recall@K >= 0.90
- Semantic Coverage >= 0.95
- Numeric Accuracy = 1.00
- Report Completeness = 1.00
- Action Coverage = 1.00

Both deterministic CI and the public real-data workflow execute the gate.

## Claim discipline

The retail dataset is observational. Promotion, display, campaign and coupon
comparisons are described as **associations / observed funnels** unless a
matched or experimental design supports causal language.
