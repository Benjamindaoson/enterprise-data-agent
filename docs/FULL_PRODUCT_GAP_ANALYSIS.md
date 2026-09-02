# Full Product Gap Analysis

Updated: 2026-09-01

This audit compares the repository with the full-product directive and frozen
architecture. Status is evidence-based; a capability is not marked complete
because its domain type or migration exists.

| Capability | Status | Evidence / gap |
| --- | --- | --- |
| Real Iowa snapshot and curated Parquet | COMPLETE | Official raw CSV partitions are curated into a measured READY snapshot. |
| Data lifecycle and manifest | COMPLETE | Ingestion/curation/validation commands, manifest, and user-facing status are present; publication automation remains out of scope. |
| Domain contracts | COMPLETE | Pydantic contracts and enums cover task, context, plan, hypothesis, execution, evidence, claims, artifacts, audit, and evaluation. |
| Semantic package | COMPLETE | Versioned YAML package includes metrics, dimensions, joins, rules, quality and access policy. |
| Context compiler | PARTIAL | The workspace compiles a bounded context from question, semantic package, policy, and snapshot; three-stage compiler and reusable typed service ports remain. |
| Analytical planner and hypotheses | PARTIAL | Deterministic plan and stateful hypotheses are implemented for the reference domain; broader task routing and model provider orchestration remain. |
| Governed execution | PARTIAL | SQL is generated from allowlisted metrics/dimensions and DuckDB reads Parquet; standalone policy, timeout, repair, and query-trace modules remain. |
| Deterministic analysis tools | PARTIAL | Aggregate, trend, contribution, and PVM tools work; richer mix-shift, reconciliation, sensitivity, and anomaly tools remain. |
| Verification | PARTIAL | Core metric/time/reproducibility validations are recorded; complete join/cardinality/causal-language rules remain. |
| Evidence-native analysis | PARTIAL | Observations, claims, and evidence are created during analysis and visible in UI; full immutable provenance graph and validation coverage remain. |
| Runtime persistence/checkpoint/replay | PARTIAL | File-backed local store, checkpoint artifact, trace, and replay endpoint work; multi-step resume remains. |
| Public API | PARTIAL | Task lifecycle, follow-up, events, plan, investigation, claims, evidence, artifacts, status, semantics, evaluation, and settings endpoints exist; auth/object-level policy adapter remains. |
| Home / Today | COMPLETE | Dataset status, recent analyses, suggestions, KPI/workspace pulse, and quick actions are available. |
| New Analysis | COMPLETE | Natural-language question entry, examples, deterministic resolution, and supported/unsupported handling work. |
| Analysis Workspace | COMPLETE | Context, status, KPI cards, findings, trend, plan, hypotheses, timeline, evidence, and report tabs are available. |
| Investigation View | COMPLETE | Hypothesis timeline and contribution ranking are rendered from task artifacts. |
| Dynamic Dashboard | PARTIAL | Data-derived KPI/trend/contribution views work; richer filters, cross-navigation, and chart/table variants remain. |
| Evidence View | COMPLETE | Claims link to evidence, observations, snapshot, metric/context versions, hashes, and validation labels. |
| Report Workspace | COMPLETE | Markdown and HTML exports are composed from existing task claims/evidence. |
| Follow-up lineage | PARTIAL | Child task creation and parent context/evidence references work; compatibility revalidation is incomplete. |
| History/reopen | COMPLETE | Tasks persist, list, and reopen in workspace; replay is not yet implemented. |
| Data Status | COMPLETE | Manifest, row count, coverage, hashes, dimensions, and warnings are exposed. |
| Semantic Explorer | COMPLETE | Metrics and business rules are inspectable in the UI. |
| Evaluation dashboard | COMPLETE | 12-case suite runs deterministically and the dashboard persists measured 12/12 results. |
| Settings | COMPLETE | Provider mode, dataset/semantic versions, budgets, and credential status are visible without secrets. |
| Provider adapter | PARTIAL | Deterministic provider path is explicit; formal provider interface and real provider implementation remain. |
| Security / audit | PARTIAL | Domain audit contract and allowlists exist; production identity and resource-level enforcement remain. |
| Testing | PARTIAL | Existing 13 contract/integration tests pass; API, analysis, frontend, E2E, data, evaluation, and replay coverage remains. |
| Documentation / startup | PARTIAL | Makefile, env example, and this audit exist; README and completion/progress reports need updating after validation. |

## Root causes found

1. The repository was a Phase 0 skeleton, not a product: API and web directories
   were absent despite the architecture describing them.
2. The curation script used prepared parameters in DuckDB `COPY ... TO`, which
   fails at runtime. It now quotes validated local paths for those statements.
3. Existing progress documentation contained unresolved merge-conflict markers
   and incorrectly treated one external download failure as a blocker for all
   independent product work.

## Audit boundary

The product is intentionally a simple modular monolith. High concurrency,
Kubernetes, distributed queues, SSO, and multi-region platformization are not
required for product completeness.
