# Resume Evidence Map — Retail BA Agent

This document maps each resume-level capability claim to concrete code, tests,
runtime evidence and measured results. It exists to prevent vague or inflated
project descriptions.

## 1. Business Semantic Reasoning

**Resume capability**

Natural-language business questions are resolved into governed
`Metric / Dimension / Time / Entity / Constraint / Intent` contracts before
execution.

**Implementation**

- `src/eiw/retail/semantics.py`
- `semantic_packages/retail_complete_journey/semantic-package.yaml`
- semantic package version/content hash carried in every response
- governed metric definitions, dimensions, joins and business rules

**Proof**

- `RetailAnalystBench-v1`: Semantic Coverage **1.000**
- `RetailAnalystBench-Rolling-v1`: Semantic Coverage **1.000** across **30
  cases / 5 historical windows**
- contract/unit tests in `tests/contract/test_retail_semantic_package.py` and
  `tests/unit/test_retail_semantics.py`

## 2. Multi-Agent Investigation and Dynamic Planning

**Resume capability**

A LangGraph Supervisor routes work to parallel Overview, Store, Product,
Promotion and Customer specialist Agents, observes typed results and can launch
a second analytical wave.

**Implementation**

- `src/eiw/retail/graph.py`
- `src/eiw/retail/planner.py`
- `src/eiw/retail/team.py`
- `src/eiw/retail/supervisor.py`
- `src/eiw/retail/specialist_policy.py`
- deterministic benchmark mode plus optional OpenAI-compatible Supervisor and
  specialist policies with allowlisted decisions and deterministic fallback

**Proof**

- dynamic re-planning added specialist workstreams in **8 / 10** benchmark
  cases
- mean initial workstreams **3.4** → mean final workstreams **4.6**
- five-specialist execution: **461.53 ms sequential** vs **330.07 ms parallel**
  in the pinned CI ablation (**1.40× wall-clock speedup**)
- policy source, selected specialist Skills and short public rationale emitted
  as runtime events

## 3. Typed Analytical Skill Engine + AI Coding

**Resume capability**

Models decide which bounded analytical capability to use; deterministic
operators execute core calculations, with an isolated code-generation lane for
open-ended analysis.

**Implementation**

- `src/eiw/retail/skills.py`
- Store contribution, anomalies, Store×Commodity scan
- Commodity contribution and Price/Volume decomposition
- Promotion/merchandising analysis
- Customer concentration, basket affinity, demographics and coupon funnel
- `src/eiw/retail/code_worker.py`
- `docker/ba-code-sandbox.Dockerfile`

**Sandbox controls**

- network disabled
- read-only root filesystem
- dropped Linux capabilities
- `no-new-privileges`
- CPU / memory / PID limits
- bounded read-only CSV snapshot
- structured JSON result contract

**Proof**

- real Docker sandbox is exercised by production-integration CI
- PostgreSQL + Redis + Docker code-sandbox integration: **8 passed**

## 4. Autonomous Insight Mining

**Resume capability**

The system scans high-dimensional analytical results, ranks high-impact
business findings and preserves the dimensions/intents explicitly requested by
the user instead of merely summarizing query output.

**Implementation**

- `src/eiw/retail/insight.py`
- Store × Commodity high-impact scan
- positive and negative contribution mining
- Price/Volume driver insights
- merchandising associations
- customer-segment and campaign/coupon insights
- query-aware dimension coverage and focused follow-up insight mining

**Proof**

`RetailHarnessAblation-v1` holds the same analytical outputs constant:

- intrinsic-score ranking Driver Recall@K: **0.900**
- query-aware ranking Driver Recall@K: **1.000**
- measured gain: **+10 pp**

This isolates a harness-level effect rather than attributing the gain to a
different model or different data.

## 5. Intelligent Visualization and Decision Delivery

**Resume capability**

Analysis results are converted into decision-oriented interactive charts and an
Executive Business Review rather than returned as a table/chat answer.

**Implementation**

- `src/eiw/retail/charts.py`
- `src/eiw/retail/report.py`
- `src/eiw/retail/export.py`
- `src/eiw/web/static/ba-demo.*`
- stateful chart/insight click drill-down via `parent_task_id + focus`
- HTML and A4 PDF report export

**Proof**

Real-data CI launches the browser product and retains:

- before/after screenshots
- WebM interaction recording
- Playwright trace
- generated HTML executive report
- generated PDF executive report

Pinned evidence: GitHub Actions run **36407672737**, artifact **10963181496**.

## 6. Evaluation, Scale and Production Engineering

**Resume capability**

The BA Agent is measured end to end for semantic correctness, numerical
correctness, driver discovery, report completeness, latency and system
behavior, rather than only SQL exact match.

**Dataset**

Pinned public CC0 Complete Journey:

- **1,469,307** transaction lines
- **20,940,529** promotion states
- **92,331** products
- **801** demographic households
- **6,589** campaign memberships
- **116,204** coupon records
- **2,102** coupon redemptions

**RetailAnalystBench-v1 — 10 real-data cases**

- Driver Recall@K: **1.000**
- Semantic Coverage: **1.000**
- Numeric Accuracy: **1.000**
- Report Completeness: **1.000**
- Action Coverage: **1.000**
- Mean time to first insight: **361.62 ms**
- End-to-end P95: **416.57 ms**

**RetailAnalystBench-Rolling-v1 — 30 cases / 5 historical windows**

- Driver Recall@K: **1.000**
- Semantic Coverage: **1.000**
- Numeric Accuracy: **1.000**
- Report Completeness: **1.000**
- Action Coverage: **1.000**
- End-to-end P95: **487.14 ms**

**CI / production proof**

- Core CI: **621 passed / 18 skipped**
- PostgreSQL + Redis + Docker code-sandbox integration: **8 passed**
- 3-request / concurrency-1 real-data smoke: **406.82 ms mean**, **407.37 ms
  P95**, **2.46 req/s**

These latency values are GitHub Actions smoke measurements, not production
capacity or external SoTA claims.

## 7. Canonical Runtime Unification

**Resume capability**

One application-level runtime owns domain dispatch instead of exposing parallel canonical runtimes.

**Implementation**

- `src/eiw/runtime/domain.py`
- `src/eiw/runtime/orchestrator.py`
- `src/eiw/retail/domain.py`
- Retail API path: `BusinessAgentRuntime → RetailDomainRuntime → RetailBARuntime`

**Proof**

- domain registration / dispatch unit coverage in `tests/unit/test_domain_runtime.py`
- final core CI on this hardening branch: **621 passed / 18 skipped**

## 8. Adversarial Evaluation + Frozen Holdout

**Resume capability**

The Agent is release-gated against ambiguity, missing data, unsupported causality, unavailable periods, prompt injection, unsafe requests, multi-turn state and malformed model outputs instead of only happy-path questions.

**Implementation**

- `src/eiw/retail/guard.py`
- `src/eiw/retail/adversarial.py`
- `evaluation/retail/frozen_holdout_v1.jsonl`
- checksum-pinned frozen holdout prevents silent mutation

**Proof**

- **210 total adversarial cases / 14 categories**
- **168 development + 42 frozen holdout**
- full CI gate: **210 / 210 passed**
- pinned Complete Journey real-data frozen holdout: **1.000 pass rate**
- security resistance: **1.000**
- malformed-model fallback recovery: **1.000**
- evidence workflow: GitHub Actions run **36437826206**, artifact **10976531496**

## 9. Comparative Model-Agent Lanes

**Resume capability**

The same BA workload can compare deterministic, single-agent, supervisor and supervisor+specialists policies under one metric schema.

**Implementation**

- `src/eiw/retail/model_lane_benchmark.py`
- `src/eiw/retail/model_telemetry.py`
- `src/eiw/retail/single_agent_policy.py`
- `.github/workflows/retail-model-lane.yml`

**Measured fields**

- task success
- estimated provider cost
- end-to-end latency
- invalid tool / choice rate
- re-plan rate
- model calls / tokens
- deterministic fallback count

**Claim boundary**

Qwen / GPT / Claude-compatible live endpoints are wired, but **no live cross-provider scores are claimed until provider credentials are configured and the manual workflow actually runs**.

## 10. Enterprise PostgreSQL Connector

**Resume capability**

A real enterprise connector covers `connect → introspect → semantic package → permissions → analysis → evidence → report`.

**Implementation**

- `src/eiw/connectors/postgres.py`
- `src/eiw/connectors/api.py`
- explicit schema/table/column allowlists
- PostgreSQL read-only transaction + statement timeout
- bounded rows and typed aggregate operations
- semantic-package and query SHA-256 evidence

**Proof**

- real PostgreSQL 16 service in GitHub Actions
- catalog introspection + semantic validation + governed aggregation + permission-denial integration test
- production integration: **8 passed**

## Resume-writing rule

The project should be described as a **Business Analysis Agent / Agentic
Analytics System**, not as a Text-to-SQL wrapper and not merely as a
Multi-Agent demo.

The strongest evidence-backed story is:

`Business semantics → Multi-Agent investigation → professional analytical
Skills → autonomous insight mining → decision delivery → end-to-end evaluation`.
