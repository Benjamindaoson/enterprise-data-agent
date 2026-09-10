# Repository Consolidation — 2026-09-10

This document records the consolidation of earlier SQL Agent / ChatBI / business analytics prototypes into `Benjamindaoson/enterprise-data-agent`.

## Canonical repository

`Benjamindaoson/enterprise-data-agent` is the canonical product line for enterprise data analysis / Enterprise Intelligence Workspace development.

The imported code under `legacy_imports/` is historical reference material. It is intentionally isolated from the canonical runtime and must not be wired into production execution without review.

## Imported sources

### deepagent_search

Source commit: `130e2a233a5ddd75c77985bc8e8032c28c69e3b1`

Deletion audit update: `a7c016e` was the final source commit before repository retirement. The follow-up audit preserved remaining unique non-IDE assets that were not in the first import, including the API wrapper, LLM/prompt-loading helpers, README, audit notes, roadmap, package metadata and lockfile.

Preserved assets:
- DeepAgents main-agent / DB-sub-agent composition;
- MySQL tool implementation;
- pharmaceutical business schema and deterministic fixtures;
- five database-agent evaluation cases;
- domain prompt rules, especially the pre-aggregate-before-JOIN rule for multiple one-to-many fact tables.

Destination: `legacy_imports/deepagent_search/`

Risk note: the historical SQL executor accepts arbitrary SQL text. It is reference-only and does not replace the governed read-only execution path in the canonical product.

### iquery-agentic-chatbi-platform

Source commit: `3b326593206277ca80d5c2f56c4898595dff6de3`

Deletion audit update: `1725332` was the final source commit before repository retirement. The follow-up audit preserved remaining unique source, tests, requirements, compact data fixtures, knowledge markdown and architecture artifacts. Binary course documents and office/PDF archives remain intentionally excluded.

Preserved assets:
- SQL / DataFrame / Python analysis tool concepts;
- tool registry;
- ReAct-style planner;
- action executor, retry history and chart tracking ideas.

Destination: `legacy_imports/iquery_chatbi/`

Risk note: the historical Python tool uses dynamic `exec`, and the historical SQL path is not a sufficient production sandbox. These files are design references only. Migrated SQL copies use environment variables instead of hard-coded credentials.

### enterprise-business-analytics-agent

Source commit: `54a1e28f0b667ff500c77c695f7b85efd473dd33`
Python subtree: `2863cfa0ad1f7fd07c5c8db46fa8332ed0c2cb3c`

Deletion audit update: `28e7022` was the final `enterprise-business-analytics-agent` commit before repository retirement. The follow-up audit also checked `crossborder-ops-agent @ 607ff24`, which retained the product-line Java/Vue teaching implementation and fuller Python hardening snapshot.

Preserved assets:
- local/JWT and OIDC/JWKS authentication reference;
- request observability and OpenTelemetry instrumentation;
- memory/Redis rate-limit designs;
- cross-border operations SQLAlchemy domain models;
- business metric services;
- cross-border evaluation cases.

Destination: `legacy_imports/crossborder_ops_python/`

Additional destination: `legacy_imports/crossborder_ops_java/`

The earlier Java/Vue teaching implementation is preserved as historical product-line reference but is not promoted into the canonical runtime. The cross-border business domain may later be rebuilt as a versioned domain/semantic package using the canonical product contracts.

### data-ananlysis-demo

Source tree/commit snapshot: `68f08e5c93b139cf44a9d2a616fdd535cd8ae4fd`

Preserved assets:
- application routing and navigation shell;
- analysis status/state types;
- Today / scope-confirmation interaction;
- mock dataset, semantic metrics, findings and evaluation fixtures;
- mock AppContext analysis-state simulation.

Destination: `legacy_imports/data_analysis_ui/`

Important: this prototype contains simulated analyses and mock evaluation values. They are not measured product evidence and must never be presented as canonical evaluation results. The canonical product must continue to derive claims, dashboards and evaluation results from real execution/evidence.

The Figma-specific cache, generated preview machinery, large imported PNG screenshots and package lockfile were intentionally not copied into the canonical product repository.

## Intentionally excluded material

The consolidation does not import:
- `.venv`, `node_modules`, IDE caches or generated build products;
- raw course archives, PDFs, large datasets or model weights;
- secret environment files, API keys, tokens or cookies;
- duplicated lockfiles and machine-specific paths;
- large Figma screenshot assets that are not needed by the canonical runtime.

## Development rule after consolidation

New enterprise data-analysis work belongs in the canonical modules of `enterprise-data-agent`, not inside `legacy_imports/` and not in the source repositories above.

Promote a legacy idea only by re-implementing or adapting it behind the canonical contracts, tests, governed execution, evidence and evaluation layers. Do not import legacy modules directly into the production import graph.
