# Enterprise Intelligence Workspace

Built on Enterprise Data Agent Platform.

Enterprise Intelligence Workspace turns a business question into a structured
investigation, governed data execution, evidence-backed findings, and a
shareable report. The reference domain is Iowa liquor wholesale order
intelligence.

## Quick start

Requirements: Python 3.12+.

```bash
make setup
make data
make dev
```

Open http://127.0.0.1:8000. The local deterministic provider is credential-free
and clearly labeled in the UI. PostgreSQL is available with
`docker compose up -d postgres` for production-shaped persistence experiments.

## Capabilities

- natural-language metric and period resolution;
- versioned semantic context and structured analysis plans;
- read-only DuckDB execution over immutable Parquet;
- trend, comparison, contribution, and mix-sensitive analysis;
- stateful hypotheses, observations, claims, evidence, and validation;
- workspace views, history, follow-up lineage, and Markdown/HTML reports;
- dataset status, semantic explorer, quality dashboard, and settings;
- explicit clarification for unsupported store-profit/net-profit questions.

## Architecture

```text
Browser → FastAPI modular monolith → Analysis Service
                                  ├─ semantic package
                                  ├─ governed DuckDB → curated Parquet
                                  ├─ evidence/artifact composer
                                  └─ durable local store
```

The full design history is in
[docs/architecture-development-baseline.md](docs/architecture-development-baseline.md),
[docs/core-module-design.md](docs/core-module-design.md), and
[docs/FULL_PRODUCT_GAP_ANALYSIS.md](docs/FULL_PRODUCT_GAP_ANALYSIS.md).

## Data and trust

The frozen snapshot is `iowa_liquor_snapshot_2026_07_v1`, covering 2024-01-01
through 2026-07-31. It represents Iowa Class E wholesale order activity, not
consumer POS sales, store profit, or net profit. Cost and spread metrics are
valid only from 2025-07-01 onward. Raw data is retained for audit; curated facts
preserve event-time attributes and the exact-duplicate policy.

Important findings link to observations, computations, result hashes, dataset
snapshot, semantic version, context version, and validation labels.

## Tests and evaluation

```bash
make test
make lint
make evaluation
```

The initial suite contains 12 Golden Cases. The quality dashboard reports it as
loaded but not run until a deterministic scorer produces measured results; no
evaluation scores are invented.

## Project structure

- `src/eiw/domain` — framework-independent contracts;
- `src/eiw/workspace` — data access, workflow, and local persistence;
- `src/eiw/app.py` — public API and web application;
- `src/eiw/web/static` — workspace UI;
- `scripts` — ingestion and curation commands;
- `semantic_packages` — versioned domain semantics;
- `data/fixtures` — controlled synthetic edge-case fixtures only;
- `docs` — architecture, ADRs, progress, and gap analysis.

## Current limitations

The reference product uses a deterministic offline provider and file-backed
local store by default. Full checkpoint/replay, formal provider adapters,
richer PVM/mix tooling, complete Golden evaluation, and enterprise-scale IAM
remain follow-on work. See
[docs/FULL_PRODUCT_PROGRESS.md](docs/FULL_PRODUCT_PROGRESS.md).
