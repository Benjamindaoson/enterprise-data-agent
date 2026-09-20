<div align="center">

# Enterprise Business Intelligence & Autonomous Operations Agent

**Governed Autonomous Analytics + Business Operations Platform**
**企业级商业智能与自主经营智能体平台**

*Autonomous multi-agent analytics for long-horizon business investigation.*

`Agent Systems` · `Business Intelligence` · `Autonomous Operations` · `Skill Runtime` · `Long-Term Memory` · `Multi-Agent` · `Semantic Layer` · `Governed NL2SQL` · `OpenTelemetry`

---

## Business operations upgrade

The analytical core now also exposes a governed business-operations layer for:

- **Business Analytics** — self-service metrics, multi-dimensional analysis, attribution and evidence-backed reporting;
- **Marketing Budget** — constrained allocation proposals and scenario simulation, with approval required before financial commitment;
- **Sales Expansion** — merchant/account opportunity ranking and governed CRM handoff proposals;
- **Monetization** — opportunity discovery, product matching and revenue simulation.

New runtime primitives include a typed **Skill Registry**, layered
**working/episodic/semantic/procedural memory**, explicit tool/token budgets,
permission checks, idempotent action contracts and **Human-in-the-loop** gates.

Public integrations remain honest by design: campaign/CRM/monetization writes
are proposal/dry-run only until real external systems are connected.

See [Business Intelligence & Autonomous Operations Upgrade](docs/business-intelligence-autonomous-operations.md).

## P9–P12: hard benchmark, real data, real LLM and production runtime

The project now has a second evaluation layer beyond the original deterministic
analytics suite:

- **BusinessAgentBench-Hard-v1** — partial observability, noisy/conflicting
  evidence, tool failure, delayed reward, memory dependence, context drift,
  unsafe writes, multiple valid paths and replanning;
- **BusinessAgentBench-RealData-v1** — official UCI Bank Marketing and Online
  Retail sources plus the existing pinned Iowa analytics snapshot;
- **Real open-weight LLM path** — causal-LM action selection, held-out
  evaluation, LoRA SFT and action-level GRPO-style optimization;
- **Production hardening** — PostgreSQL trajectories/checkpoints/approvals,
  Redis queue, async worker, model routing, token/dollar cost accounting,
  OpenTelemetry metrics, Prometheus/Grafana and regression gates.

The real-data benchmark explicitly covers **Analytics, Attribution, Marketing
Budget, Sales Expansion, Monetization, Tool Use, Recovery and Safety**.

The normal CI verifies the hard environment, small-policy SFT/GRPO, the full
official Bank Marketing + Online Retail benchmark, and PostgreSQL/Redis
integration. Real Qwen/Llama-class training lives in a separate manual
self-hosted workflow so the repository does not pretend a large-model
experiment ran when GPU compute was unavailable.

Measured held-out Hard-v1 results (12 cases) are:

| Policy | Success | Avg reward | Invalid action | Policy violation |
| --- | ---: | ---: | ---: | ---: |
| Direct | 0.0% | -3.7627 | 90.63% | 75.0% |
| Random | 0.0% | -3.8506 | 72.0% | 91.67% |
| Prompt heuristic | 58.33% | 0.0115 | 19.54% | 0.0% |
| SFT | 66.67% | 0.5926 | 11.63% | 8.33% |
| SFT + GRPO | 66.67% | 0.6395 | 10.59% | 8.33% |

GRPO therefore shows a **measured reward / action-validity improvement without
a task-success uplift** on this run; the repository does not claim otherwise.

The RealData-v1 CI build parses **45,211 Bank Marketing rows** and **541,909
Online Retail rows** and generates nine grounded benchmark tasks.

See [P9–P12 Execution Report](docs/P9_P12_EXECUTION_REPORT.md).

---

## Implementation Status

| Capability | Status | Notes |
|------------|--------|-------|
| Agent Runtime / Harness | ✅ VERIFIED | Supervisor, durable state, checkpoint/resume, recovery |
| Governed NL2SQL + Semantic Layer | ✅ VERIFIED | SQLGlot, versioned business semantics, evidence |
| Skill + Layered Memory | ✅ VERIFIED | Typed skill registry; working/episodic/semantic/procedural memory |
| Business Operations | ✅ VERIFIED | Analytics, marketing budget, sales expansion, monetization |
| BusinessAgentBench-Hard-v1 | ✅ VERIFIED | Long-horizon faults, memory, safety, replanning |
| BusinessAgentBench-RealData-v1 | ✅ VERIFIED | Bank Marketing + Online Retail + Iowa analytics |
| Trajectory / Eval Flywheel | ✅ VERIFIED | Replay, failure mining, SFT export, policy metrics |
| Small-policy SFT | ✅ VERIFIED | Held-out success 66.67% vs prompt 58.33% |
| Small-policy GRPO | ✅ VERIFIED | Reward 0.5926 → 0.6395; invalid actions 11.63% → 10.59% |
| PostgreSQL Durable Runtime | ✅ VERIFIED | Trajectory, checkpoint, approval round trips in CI |
| Redis Async Queue | ✅ VERIFIED | Queue round trip and worker retry in CI |
| OTel / Prometheus / Grafana | ✅ IMPLEMENTED | Metrics + provisioned local observability stack |
| Canary / Regression Gate | ✅ VERIFIED | Success, safety, invalid-action and cost thresholds |
| Real open-weight LLM evaluation | ⚠️ IMPLEMENTED | Qwen causal-LM policy + held-out evaluator; GPU run not yet measured |
| Real LLM LoRA SFT / GRPO | ⚠️ IMPLEMENTED | Manual self-hosted workflow; no fabricated gain claim |
| Proprietary CRM / campaign writes | 🔒 NOT CONNECTED | Public version remains dry-run / approval-gated |

**Core CI:** 535 passed / 2 skipped  
**Training CI:** 7 passed  
**Production integration:** 6 passed  
**RealData-v1:** 45,211 Bank Marketing rows + 541,909 Online Retail rows  
**Evaluation Cases:** existing 245+ deterministic cases + BusinessAgentBench suites

---

## Why this is not another NL2SQL demo

```text
Business Question
      ↓
Resolve Business Semantics
      ↓
Plan Investigation
      ↓
Choose Analytical Action
      ↓
Execute Governed Data Tool
      ↓
Observation → Hypothesis Update
      ↓
Claim → Evidence → Verification
      ↓
Replan / Drill Down / Clarify / Finish
```

The core idea is simple:

> **The model decides what to analyze next; deterministic tools decide how the data is executed.**

---

## Why this is not another NL2SQL demo

| | Typical NL2SQL / ChatBI | Enterprise Data Agent |
| --- | --- | --- |
| Unit of work | One query | Durable analysis task |
| Reasoning | Generate SQL and summarize | Plan, observe, replan, verify |
| State | Prompt / chat history | Persistent task state |
| Business semantics | Schema hints in prompt | Versioned Semantic Layer |
| Data execution | Model-generated query logic | Bounded analytical operators + governed tools |
| Multi-agent coordination | Free-form conversation | Supervisor + structured handoff + shared state |
| Verification | Usually implicit | Claim → Evidence → Verification |
| Failure handling | Retry from the beginning | Trace, checkpoint, recovery, replay |

---

## Core design

### 1. Controlled multi-agent coordination

Long-running analysis becomes unstable when agents coordinate through unrestricted conversation: tasks are repeated, context drifts, and different agents may hold conflicting state.

Enterprise Data Agent uses a **Supervisor–Executor architecture**, **shared task state**, and **structured handoffs**.

- the **Supervisor** owns decomposition, routing, replanning, and stop decisions;
- specialized executors work inside bounded responsibilities;
- agents exchange structured observations through shared state instead of maintaining independent conversational memory;
- every meaningful step is traceable back to the task state.

```text
                    ┌───────────────┐
Business Question → │  Supervisor   │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ Shared State  │
                    └───────┬───────┘
                            ↓
                 Specialized Executors
                            ↓
              Observation / Evidence / Status
                            ↓
                    Supervisor replans
```

### 2. Long-horizon runtime and context engineering

A long analysis task may accumulate plans, tool calls, query results, intermediate findings, failed attempts, and verification records. Replaying the entire trajectory into every model call increases cost and degrades context quality.

The runtime separates **durable task state** from **model context**:

- plans, actions, tool outputs, observations, claims, and validation results live outside the prompt;
- checkpoint and trace records preserve execution progress;
- context is assembled dynamically for the current role and subtask;
- retry, timeout, recovery, and replay are runtime concerns rather than prompt tricks.

This keeps the model context focused on the information required for the current decision while preserving the full task history externally.

### 3. Versioned Semantic Layer

Enterprise analytics is difficult because business meaning changes across regions, categories, and business units. The same term may map to different formulas, time rules, filters, joins, or availability windows.

Enterprise Data Agent separates business semantics from the Agent Core through a versioned **Semantic Layer**.

A semantic package can define:

- metrics and calculation rules;
- dimensions and allowed relationships;
- time semantics and data availability;
- business and quality rules;
- access policies and supported analytical capabilities.

The Agent Runtime therefore reasons against a stable semantic contract while business-specific definitions can evolve independently.

### 4. Typed analytical operators instead of unconstrained query generation

The agent is not asked to invent arbitrary SQL as its primary reasoning interface. Its action space is expressed through **typed analytical operators** such as:

- compare periods;
- inspect trends;
- break down by dimension;
- rank contributors;
- drill into anomalies;
- test a working hypothesis.

The agent selects the next analytical action from the current **Observation + Hypothesis + Task State**. A deterministic data layer executes the bounded operation and returns a structured result.

```text
Observation + Hypothesis
          ↓
Choose Next Analysis
          ↓
Typed Analytical Operator
          ↓
Deterministic Data Tool
          ↓
Structured Observation
          ↓
Update State / Replan / Finish
```

This moves the model's responsibility from **"write the query"** to **"decide the next useful analytical step."**

### 5. Evidence-backed verification

A correct query does not guarantee a correct business conclusion. An agent can still over-attribute a cause, ignore conflicting evidence, or turn an observation into a claim that the data does not support.

Enterprise Data Agent therefore treats claims and evidence as first-class objects.

```text
Observation
    ↓
Claim
    ↓
Evidence
    ↓
Verification
    ↓
Accept / Replan / Clarify / Reject
```

Important claims can be linked to the metric definition, query result, intermediate computation, dataset snapshot, semantic version, and validation result. Verification writes back into task state and can trigger additional investigation rather than allowing an unsupported conclusion into the final report.

---

## Architecture

```mermaid
flowchart TD
    Q[Business Question] --> S[Supervisor]
    S --> TS[(Shared Task State)]

    TS --> C[Context Assembly]
    SL[Versioned Semantic Layer] --> C
    C --> A[Analyst / Executor]

    A --> OP{Typed Analytical Operator}
    OP --> T[Governed Data Tools]
    SL --> T
    T --> D[(Business Data)]
    T --> O[Observation]

    O --> TS
    O --> H[Hypothesis Update]
    H --> S

    O --> CL[Claim]
    CL --> E[Evidence]
    E --> V[Verification]

    V -->|needs more analysis| S
    V -->|needs clarification| U[Business User]
    V -->|verified| R[Findings / Report]

    TS --> RT[Trace / Checkpoint / Replay]
```

---

## Example analysis loop

A question such as:

> **Why did Category A sales decline last month?**

is not treated as a single SQL request. A typical investigation may become:

1. resolve the metric, period, category, and comparison baseline;
2. compare current vs. prior period;
3. break the change down by store, product, or supplier;
4. rank the largest contributors;
5. inspect abnormal segments;
6. update or reject the working hypothesis;
7. verify the final claim against the underlying evidence;
8. produce findings with traceable support.

The exact path is determined by intermediate observations rather than fixed in advance.

---

## Public reference implementation

This repository is the publishable reference implementation of the architecture above. Proprietary business data, internal rules, and private integrations are replaced with reproducible public data and controlled fixtures.

The current public dataset uses **Iowa Class E wholesale order activity** and contains **6,484,227 curated fact rows** covering **2024-01-01 through 2026-07-31**. It is used to exercise the analytical contracts and runtime without exposing private business information.

The public implementation currently includes:

- versioned semantic packages;
- durable task and domain contracts;
- plans, hypotheses, observations, claims, evidence, and validation models;
- deterministic aggregate, trend, comparison, contribution, and PVM-style analysis paths;
- governed analytical execution;
- checkpoint artifacts, trace events, SSE task events, and replay surfaces;
- task history, investigation views, evidence inspection, and Markdown / HTML reports;
- reproducible data curation and validation commands.

The public codebase intentionally does **not** claim to reproduce every proprietary production integration. Full Supervisor–Executor orchestration, richer role-scoped context assembly, and complete multi-step resume are being rebuilt on top of the public contracts.

---

## Quick start

Requirements: **Python 3.12+**

```bash
make setup
make data
make dev
```

Open:

```text
http://127.0.0.1:8000
```

Optional PostgreSQL persistence:

```bash
docker compose up -d postgres
```

Run checks:

```bash
make test
make lint
make evaluation
```

---

## Public implementation stack

- **Python 3.12**
- **FastAPI / Pydantic**
- **SQLAlchemy / Alembic**
- **PostgreSQL** persistence contracts
- **OpenTelemetry** instrumentation
- **SQLGlot** SQL parsing / validation support
- **DuckDB + Parquet** only for the reproducible local analytical reference path

DuckDB is used here as an embedded public-data execution engine for reproducibility; it is not presented as the production data-warehouse architecture.

---

## Project structure

```text
src/eiw/domain/          Domain contracts and task-state models
src/eiw/semantic/        Versioned semantic packages
src/eiw/workspace/       Analysis workflow and data execution
src/eiw/persistence/     Durable relational persistence contracts
src/eiw/app.py           FastAPI application and task APIs
src/eiw/web/static/      Analysis workspace UI
semantic_packages/       Business semantics and rules
scripts/                 Ingestion, curation, validation
validation/              Independent data validation
evaluation/              Golden tasks and deterministic evaluation
data/fixtures/           Controlled failure-mode fixtures
docs/                    Architecture, ADRs, progress, gap analysis
```

---

## Design documentation

- [`Architecture Development Baseline`](docs/architecture-development-baseline.md)
- [`Core Module Design`](docs/core-module-design.md)
- [`Full Product Progress`](docs/FULL_PRODUCT_PROGRESS.md)
- [`Full Product Gap Analysis`](docs/FULL_PRODUCT_GAP_ANALYSIS.md)

---

## Design principle

> **Autonomous analysis should be stateful, semantically grounded, recoverable, and verifiable — not just fluent.**
