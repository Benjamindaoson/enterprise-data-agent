# Build Progress

Updated: 2026-09-01 UTC.

The repository began as a Phase 0 contract skeleton. The full-product build
now includes a runnable FastAPI workspace, a deterministic analytical workflow,
real curated Iowa data, evidence/report artifacts, and a browser UI.

## Verified milestones

- 6,484,227 curated fact rows covering 2024-01-01 through 2026-07-31;
- 20 exact raw duplicates measured and removed according to ADR-002;
- current Store/Product dimension joins reconcile to row count and sales;
- 16 automated tests pass;
- 12/12 initial Golden Cases pass in the deterministic local runner;
- `make dev` serves the workspace and public task/resource APIs.

## Remaining work

See [FULL_PRODUCT_GAP_ANALYSIS.md](FULL_PRODUCT_GAP_ANALYSIS.md) and
[FULL_PRODUCT_PROGRESS.md](FULL_PRODUCT_PROGRESS.md). Remaining items are
follow-on hardening: richer deterministic tools, checkpoint/replay, formal
provider adapters, complete resource-level identity enforcement, and browser
E2E coverage.

The external download blocker from the earlier MVP report is isolated to future
fresh acquisition. It does not block analysis over the verified local snapshot
or independent product development.
