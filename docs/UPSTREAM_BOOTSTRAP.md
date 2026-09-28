# BA Agent upstream bootstrap

## Goal

Bootstrap the production BA Agent by reusing mature open-source implementations first, prove the full product path,
then replace upstream internals behind stable first-party interfaces.

This is an acceleration phase, not the final architecture.

## Product boundary

The first-party product remains responsible for:

1. Business-analysis orchestration and multi-agent investigation.
2. Retail analytical skills and deterministic calculation contracts.
3. Automated insight mining and ranking.
4. Executive business-report schema and decision/action artifacts.
5. RetailAnalystBench / BusinessAnalystBench and product performance evaluation.

The upstream projects are implementation accelerators for generic infrastructure.

## Upstream roles

### DeepAnalyze

Use for:
- code-analysis worker;
- multi-round code -> execute -> observe loop;
- optional DeepAnalyze-8B inference through an OpenAI-compatible/vLLM endpoint;
- reference training recipes only.

Do not make the BA Agent runtime depend directly on DeepAnalyze internals. Wrap it behind an AnalystWorker interface.

### Data Formulator

Use for:
- interactive Data Thread UX;
- data workspace patterns;
- chart generation/restyling;
- report composition patterns;
- DuckDB and code-sandbox implementation reference.

The final BA Agent UX should preserve its own product identity and report schema.

### WrenAI

Use for:
- semantic-model concepts;
- governed NL2SQL/query planning;
- business context and metric definitions;
- connector/SDK reference.

Only Apache-2.0 paths (`core/**`, `sdk/**`, `skills/**`, `examples/**`) are approved for code reuse in the
first-party tree. Do not copy documentation or future AGPL paths without an explicit license review.

## Pinning

All upstreams are pinned as Git submodules to exact commits. Upgrades must be explicit and must pass
`python scripts/verify_upstreams.py`.

## Replacement strategy

Replacement order after the integrated demo works:

1. Define stable internal interfaces around each reused capability.
2. Add contract tests and a benchmark baseline.
3. Reimplement one upstream-backed capability at a time.
4. Run the same contract tests/benchmarks.
5. Remove the upstream dependency only after parity or improvement is demonstrated.

This prevents a rewrite from silently degrading product quality.


## Replacement progress

- Data Formulator visualization/product shell: first-party BA demo, chart
  planner/restyler, report export and Playwright product proof are implemented.
- Wren semantic concepts: first-party versioned retail semantic package and
  governed analytical data contracts are implemented.
- DeepAnalyze code lane: a first-party OpenAI-compatible code generator plus
  Docker-isolated execution worker is implemented and preferred; DeepAnalyze
  remains only as a bootstrap fallback/reference until the replacement has
  broader model benchmarks.
