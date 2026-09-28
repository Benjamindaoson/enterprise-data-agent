# BA Agent OSS bootstrap - completed

## Why this document exists

The Retail BA Agent was initially bootstrapped by evaluating mature open-source
Data-Agent projects, then replacing the generic pieces behind stable internal
contracts. The replacement phase is complete for the product path in the
current repository: no DeepAnalyze, Data Formulator, or WrenAI source tree is
vendored or required at runtime.

## What was replaced

| Bootstrap reference | First-party replacement |
| --- | --- |
| Data Formulator product/visualization ideas | `src/eiw/web/static/ba-demo.*`, `retail/charts.py`, HTML/PDF report export, Playwright product proof |
| WrenAI semantic-model ideas | versioned `semantic_packages/retail_complete_journey`, semantic resolver, governed join/metric contracts |
| DeepAnalyze code-analysis loop | `retail/code_worker.py`: OpenAI-compatible code generator + repository-owned Docker sandbox |
| Generic agent orchestration | LangGraph investigation graph + optional model-driven Supervisor + deterministic fallback |
| Generic data-agent evaluation | `RetailAnalystBench-v1` with independent read-only SQL gold |

## Stable first-party product boundary

The current Retail Intelligence path owns:

1. business semantic resolution;
2. Supervisor planning and re-planning;
3. parallel specialist analysts;
4. typed retail analytical skills;
5. high-dimensional insight mining;
6. stateful scope-aware follow-ups;
7. intelligent chart planning/restyling;
8. executive HTML/PDF reports;
9. bounded AI Coding in a Docker sandbox;
10. real-data ingestion, benchmark, latency smoke and browser product proof.

## External compatibility

DeepAnalyze may still be used as an externally hosted optional fallback through
`EIW_DEEPANALYZE_URL`. This is a compatibility adapter only; no upstream
source is included in this repository.

## Replacement gate

The project did not remove the bootstrap source until the first-party path had:

- contract/unit coverage;
- real-data RetailAnalystBench regression gates;
- PostgreSQL/Redis production integration;
- Docker sandbox integration testing;
- Playwright real-data UI/report/video proof.

This document is retained as architecture history, not as an instruction to
initialize Git submodules.
