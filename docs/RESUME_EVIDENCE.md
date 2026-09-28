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
- PostgreSQL + Redis + Docker code-sandbox integration: **7 passed**

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

- Core CI: **613 passed / 17 skipped**
- PostgreSQL + Redis + Docker code-sandbox integration: **7 passed**
- 3-request / concurrency-1 real-data smoke: **406.82 ms mean**, **407.37 ms
  P95**, **2.46 req/s**

These latency values are GitHub Actions smoke measurements, not production
capacity or external SoTA claims.

## Resume-writing rule

The project should be described as a **Business Analysis Agent / Agentic
Analytics System**, not as a Text-to-SQL wrapper and not merely as a
Multi-Agent demo.

The strongest evidence-backed story is:

`Business semantics → Multi-Agent investigation → professional analytical
Skills → autonomous insight mining → decision delivery → end-to-end evaluation`.
