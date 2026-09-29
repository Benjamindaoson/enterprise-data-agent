> **Portfolio status / 作品集状态：FLAGSHIP · Agent Systems**
> Canonical independent flagship repository; indexed by Agent Systems Lab.

<div align="center">

# BA Agent｜商业分析智能体

**Autonomous Business Analysis · Insight Mining · Decision Reports**

A production-shaped **Business Analysis Agent (BA Agent)** that understands business semantics, dispatches specialist analysts, autonomously investigates performance, discovers high-impact drivers and opportunities, and delivers interactive decision-ready reports.

`BA Agent` · `Multi-Agent` · `LangGraph` · `Business Intelligence` · `Semantic Layer` · `Analytical Skills` · `AI Coding` · `Insight Mining` · `Evaluation`

</div>

---

## Why this is not Text-to-SQL / ChatBI

| Typical ChatBI boundary | BA Agent capability | Measured / executable proof |
| --- | --- | --- |
| Question → SQL | **Business semantic reasoning** | 1.000 Semantic Coverage on 10-case + 30-case rolling suites |
| User asks the next question | **Supervisor-driven autonomous investigation** | dynamic re-plan added specialists in 8/10 cases |
| One SQL/tool call | **Independent specialist Agents + typed analytical Skills** | Store / Product / Promotion / Customer skill allowlists and runtime events |
| Summarize returned rows | **Programmatic insight mining** | query-aware ranking improves Driver Recall@K from 0.90 → 1.00 in same-output ablation |
| Table / default chart | **Decision-oriented visualization + report delivery** | real Playwright UI, HTML + A4 PDF product proof |
| SQL exact match | **End-to-end analyst evaluation** | 30 cases × 5 historical windows with independent SQL gold |

See [the resume/evidence map](docs/RESUME_EVIDENCE.md) for the exact implementation and proof behind each capability.

For the self-evolving semantic layer, see [Semantic Evolution Evidence](docs/SEMANTIC_EVOLUTION_EVIDENCE.md), including the four-way blind PostgreSQL onboarding ablation and its exact CI artifact.

## Retail Intelligence reference product

The first high-fidelity product vertical is a **Retail Business Analysis Agent (BA Agent)**. It is intentionally broader than Text-to-SQL:

```text
Business question
      ↓
Business semantics
      ↓
Supervisor + parallel analytical workstreams
      ↓
SQL / deterministic analytical skills / optional code worker
      ↓
Store · Product · Promotion · Customer investigation
      ↓
Programmatic insight mining
      ↓
Decision-oriented charts
      ↓
Executive Business Review + action cards
```

Run the end-to-end demo at `/ba`. A deterministic fixture is available for zero-setup development, while the real-data path can download and materialize the public CC0 `completejourney` distribution automatically:

```bash
make setup-retail-data
make retail-data
EIW_RETAIL_DATA_DIR=$PWD/data/retail make dev
```

The pinned real-data baseline currently contains **1,469,307 transaction lines**, **20,940,529 promotion states**, **92,331 products**, **801 demographic households**, **6,589 campaign memberships**, **116,204 coupon records**, and **2,102 coupon redemptions**. Source commit, source/Parquet SHA-256 hashes, row counts and column manifests are recorded by the ingestion pipeline.

The current Retail Intelligence product path is first-party. DeepAnalyze, Microsoft Data Formulator and WrenAI were evaluated during bootstrap, but their source trees have been removed after first-party replacements passed the project benchmark and integration gates. An externally operated DeepAnalyze API remains an optional compatibility fallback only.

### Canonical runtime boundary

There is one application-level runtime:

```text
FastAPI / product surface
        ↓
BusinessAgentRuntime          ← canonical application runtime
        ↓
RetailDomainRuntime           ← domain adapter / policy boundary
        ↓
RetailBARuntime               ← domain-internal investigation agent
        ↓
Supervisor → specialists → typed analytical Skills
```

`RetailBARuntime` is no longer a second application-level canonical runtime. The FastAPI Retail routes register and invoke the Retail domain through `BusinessAgentRuntime.analyze_domain(...)`, so runtime events, domain registration and application orchestration have one owner while the Retail package keeps ownership of its domain graph.

### Retail runtime architecture

```mermaid
flowchart TD
    U[Business question / follow-up] --> BAR[BusinessAgentRuntime]
    BAR --> DR[RetailDomainRuntime]
    DR --> S[Business Semantic Engine]
    S --> SUP[Supervisor]
    SUP --> O[Overview Analyst]
    SUP --> ST[Store Analyst]
    SUP --> PR[Product Analyst]
    SUP --> PM[Promotion Analyst]
    SUP --> CU[Customer Analyst]

    O --> SK[Typed Analytical Skills]
    ST --> SK
    PR --> SK
    PM --> SK
    CU --> SK

    SK --> D[(DuckDB / Parquet)]
    SK --> C[Bounded AI Coding]
    C --> SB[Docker Sandbox]

    O --> OBS[Typed observations]
    ST --> OBS
    PR --> OBS
    PM --> OBS
    CU --> OBS
    OBS --> SUP
    SUP -->|Replan| ST
    SUP -->|Replan| PR
    SUP -->|Replan| PM
    SUP -->|Replan| CU

    OBS --> IM[Insight Mining + Query-aware Ranking]
    IM --> CH[Chart Planner / Restyler]
    IM --> RP[Executive Report + Actions]
    CH --> UI[Streaming BA Workspace]
    RP --> UI
    UI -->|click insight / chart| U
```

The Supervisor can be deterministic for reproducible evaluation or backed by an
OpenAI-compatible model with a strict workstream allowlist and deterministic
fallback. Each Store / Product / Promotion / Customer specialist can also use
its own optional model policy to choose from a bounded domain-specific Skill
allowlist; deterministic execution remains the fallback. Specialist workstreams
execute concurrently and exchange typed task state/results rather than
free-form hidden reasoning.

### Multi-Agent orchestration

The Retail domain Agent uses a LangGraph investigation loop with a Supervisor and
parallel specialist analysts for performance, stores, products, promotion and
customers. The benchmarked default planner is deterministic for reproducibility;
an optional OpenAI-compatible Supervisor can select/re-plan workstreams with an
allowlisted JSON contract and automatic deterministic fallback. Specialist
Agents optionally select their own bounded analytical Skill subsets; selected
skills, policy source and public rationale are emitted as runtime events.
Interactive follow-ups preserve the parent analysis window and carry an explicit focus
(e.g. store -> commodity or commodity -> store) rather than restarting from
chat history.

### First-party AI Coding

Open-ended analytical code is generated through a provider-neutral
OpenAI-compatible adapter and executed in a repository-owned ephemeral Docker
sandbox with network disabled, read-only root filesystem, dropped capabilities,
`no-new-privileges`, and CPU/memory/PID limits. The production-integration CI
runs the real Docker sandbox, not a mock.

### Measured Retail BA baseline

`RetailAnalystBench-v1` uses **10 deterministic BA cases with independent read-only SQL gold**, covering KPI summary, decline diagnosis, store/product drivers, cross-dimensional drill-down, price-volume decomposition, merchandising, customer/basket analysis, customer segments and executive review.

| Metric | Pinned CC0 Complete Journey |
| --- | ---: |
| Driver Recall@K | **1.000** |
| Semantic Coverage | **1.000** |
| Numeric Accuracy | **1.000** |
| Report Completeness | **1.000** |
| Action Coverage | **1.000** |
| Mean time to first insight | **288 ms** |
| End-to-end P95 | **330 ms** |

A separate 3-request, concurrency-1 GitHub Actions scale smoke measured **302 ms mean**, **309 ms P95**, and **3.31 requests/s**. These latency figures are CI smoke measurements, not production-capacity claims or external SoTA results. See [real-data benchmark notes](docs/BA_AGENT_REAL_DATA_RESULTS.md).

### Rolling-window robustness

A second `RetailAnalystBench-Rolling-v1` suite evaluates **30 BA cases across 5 historical windows**, instead of testing only the latest period. On the pinned real-data run it preserved **1.000 Driver Recall@K, Semantic Coverage, Numeric Accuracy, Report Completeness and Action Coverage** across all 30 cases; P95 end-to-end latency was **377 ms**. This is still an internal benchmark, but it reduces the risk of a one-window overfit.

### Adversarial robustness

`RetailAdversarialBench-v1` adds **210 adversarial questions across 14 failure families**:

- **168 development cases** (12 per family);
- **42 frozen holdout cases** (3 per family) stored as JSONL with a pinned SHA-256 checksum;
- paraphrase, ambiguity, impossible requests, missing data, unsupported causality, conflicting dimensions, unavailable time ranges, unseen combinations, schema distractors, unsafe prompts, prompt injection, irrelevant requests, multi-turn follow-up, and malformed model responses.

The current development gate passed **164 / 168 (97.62%)** cases; the four retained misses are all in one missing-data paraphrase family and are intentionally not hidden behind a perfect aggregate. The pinned Complete Journey real-data workflow separately ran the frozen 42-case holdout with **42 / 42 (100%) pass rate, 1.000 security resistance, and 1.000 malformed-model fallback recovery**. Combined, the two partitions pass **206 / 210** cases. This remains an internal robustness benchmark, not an external SoTA claim.

### Model-lane benchmark

The repository now has one comparison harness for four execution lanes:

| Lane | What changes |
| --- | --- |
| deterministic | no model policy |
| single-agent | one model call chooses workstreams + bounded skills |
| supervisor | model plans/re-plans; deterministic specialists execute |
| supervisor + specialists | model supervisor plus model skill selection |

The runner records **success, estimated cost, latency, invalid-tool/choice rate, re-plan rate, model calls, tokens and fallback count**. A manual GitHub Actions workflow is wired for **Qwen-, GPT-, and Claude-compatible endpoints**. Live provider scores are intentionally **not claimed until credentials/endpoints are configured and that workflow is actually run**.

### Enterprise PostgreSQL connector

A governed PostgreSQL connector now implements the full enterprise path:

```text
connect
→ catalog introspection
→ semantic-package validation/inference
→ schema/table/column allowlists
→ read-only bounded aggregate analysis
→ evidence hash + semantic hash
→ decision report
```

The integration test runs against a real PostgreSQL 16 service in CI, verifies catalog introspection, semantic-package validation, allowlisted aggregation, evidence lineage and permission rejection. Production integration is currently **8 passed** including the PostgreSQL connector, Redis, durable runtime and Docker code sandbox.

### Harness ablation

`RetailHarnessAblation-v1` holds the analytical workstream outputs constant
and removes only harness behavior. On the same 10 real-data cases, naive
intrinsic-score ranking reached **0.90 Driver Recall@K**, while query-aware
semantic selection reached **1.00 (+10 pp)**. Dynamic re-planning added
specialist workstreams in **8/10** cases. In the same GitHub-hosted smoke,
parallel specialist execution averaged **330 ms** versus **462 ms** sequentially
sequentially (**1.40× wall-clock speedup**). These are system-ablation results,
not external SoTA claims.

### Real product proof

The real-data workflow now boots the BA Agent against the pinned CC0 dataset and uses Playwright to execute the browser product end to end. CI retains a proof bundle containing:

- pre-run and completed UI screenshots;
- a recorded WebM interaction;
- Playwright trace;
- generated executive HTML report;
- generated A4 PDF report;
- exact benchmark JSON, scale JSON and dataset provenance manifest.

The same CI path also exercises the first-party Docker AI-Coding sandbox (network disabled, read-only root, CPU/memory/PID limits) and the stateful follow-up/drill-down contracts.

## What this project is

Most BA / data agents stop at:

```text
Question → SQL → Answer
```

This project targets a harder problem:

```text
Business Question
      ↓
Understand Business Semantics
      ↓
Plan Investigation
      ↓
Acquire Evidence
      ↓
Analyze / Attribute / Verify
      ↓
Make a Business Decision
      ↓
Propose or Execute an Action
      ↓
Observe Outcome
      ↓
Evaluate / Learn / Improve
```

The system is designed around one principle:

> **One canonical runtime owns application orchestration; governed deterministic services own execution, while model-driven policies are evaluated and promoted through explicit Agent-learning lanes.**

The FastAPI surface now routes analytical requests, follow-ups, capability discovery and business-operation planning through `BusinessAgentRuntime`. The default public analytical lane remains deterministic and reproducible; model-driven action policies are kept behind explicit evaluation/post-training boundaries instead of being silently presented as production behavior.

The result is not a single-call NL2SQL or ChatBI demo, but a **stateful, auditable BA Agent runtime** that connects governed analytics with approval-gated business operations.

## Product preview

### Final architecture

![BA Agent Architecture](docs/assets/system-architecture.svg)

### Demo console

![Autonomous Operations Console](docs/assets/demo-console.svg)

Run the Retail Intelligence product locally:

```text
http://127.0.0.1:8000/ba
```

The legacy operations console remains available separately; the `/ba` surface
is the product demo used by the real-data Playwright proof.

---

## Verified results

### Engineering

| Area | Verified status |
| --- | ---: |
| Core CI | **621 passed / 18 skipped** |
| Post-training tests | **7 passed** |
| PostgreSQL + Redis + Docker code sandbox + enterprise connector integration | **8 passed** |
| Hard benchmark acceptance gate | **PASS** |
| UCI real-data benchmark | **587,120 rows parsed in CI** |

The real-data benchmark currently parses:

- **45,211** UCI Bank Marketing rows;
- **541,909** UCI Online Retail rows;
- the existing pinned Iowa wholesale analytical snapshot with **6,484,227** curated fact rows.

### BusinessAgentBench-Hard-v1

Held-out evaluation on 12 long-horizon cases:

| Policy | Success | Avg. reward | Invalid action | Policy violation |
| --- | ---: | ---: | ---: | ---: |
| Direct | 0.00% | -3.7627 | 90.63% | 75.00% |
| Random | 0.00% | -3.8506 | 72.00% | 91.67% |
| Prompt heuristic | 58.33% | 0.0115 | 19.54% | 0.00% |
| **SFT** | **66.67%** | 0.5926 | 11.63% | 8.33% |
| **SFT + GRPO** | **66.67%** | **0.6395** | **10.59%** | 8.33% |

The current result is intentionally reported as:

> **SFT improves task success over the prompt baseline; GRPO further improves reward and action validity, but does not improve task success on this run.**

The CI acceptance gate enforces this result class instead of allowing a training change to silently regress reliability.

---

## Business scenarios

The BA Agent uses one runtime to support four closely related business-analysis and operations families.

### 1. Business Intelligence

Typical tasks:

- self-service data analysis;
- multi-dimensional drill-down;
- contribution analysis;
- Price / Volume / Mix decomposition;
- anomaly investigation;
- evidence-backed attribution;
- business reporting and visualization.

Example:

> Why did a region's sales decline, which segments contributed most, and what evidence supports the conclusion?

### 2. Marketing Budget

Typical tasks:

- historical campaign performance analysis;
- channel / segment comparison;
- constrained budget allocation;
- scenario simulation;
- ROI-oriented recommendations;
- approval-gated campaign actions.

Example:

> How should the remaining marketing budget be allocated across eligible segments under a fixed budget and risk limit?

### 3. Sales Expansion

Typical tasks:

- merchant / account segmentation;
- opportunity ranking;
- capacity-constrained lead prioritization;
- evidence-backed CRM handoff.

Example:

> Which merchants should the sales team prioritize when only a limited number of accounts can be contacted?

### 4. Monetization

Typical tasks:

- opportunity discovery;
- product / offer matching;
- customer-value analysis;
- revenue simulation;
- retention and cancellation-risk-aware recommendations.

---

## System architecture

```mermaid
flowchart TD
    U[Business User / API] --> R[BusinessAgentRuntime]

    R --> A[Deterministic Semantic Analytics Lane]
    R --> B[Business Operations Lane]
    R --> M[(Layered Episodic / Semantic / Procedural Memory)]

    A --> SL[Versioned Semantic Layer]
    SL --> N[Governed NL2SQL / Analytical Tools]
    N --> D[(Business Data)]
    D --> O[Observation / Evidence]
    O --> V[Claim-Evidence Verification]
    V --> R

    B --> SK[Typed Skill Registry]
    SK --> G[Permission / Budget / HITL Gate]
    G --> X[Dry-run / Approval-gated External Actions]

    R --> OT[OpenTelemetry / Runtime Events]
    OT --> P[Prometheus / Grafana]

    TR[Trajectory / Replay] --> E[BusinessAgentBench Evaluation]
    E --> FM[Failure Mining]
    FM --> PT[SFT / GRPO]
    PT --> RG[Regression / Acceptance Gate]
    RG --> E
```

---

## Core capabilities

### Agent Runtime / Harness

`BusinessAgentRuntime` is the canonical application-layer facade used by the FastAPI surface. It composes the verified analytical workflow, business-operation planner, typed Skills, layered memory and governance contracts without duplicating their implementations.

Implemented capabilities include:

- one application entry point for analysis, follow-ups and business-operation planning;
- explicit runtime lane metadata and observable runtime events;
- persistent analytical Task State and evidence lineage;
- checkpoint / replay APIs;
- layered episodic / semantic / procedural memory contracts;
- typed Skill registration and permission requirements;
- tool/token budgets and approval-gated high-risk actions;
- PostgreSQL / Redis production adapters;
- trajectory-based evaluation, SFT / GRPO and regression gates.

A model-driven Supervisor–Executor implementation remains available as an agentic/research path, but the public default analytical API is deliberately deterministic until model-driven behavior is promoted through reproducible evaluation.

---

### Versioned Semantic Layer

Business questions are resolved against governed semantic contracts instead of raw schemas.

Semantic packages can define:

- metrics and formulas;
- dimensions;
- allowed joins;
- time semantics;
- data-availability windows;
- business rules;
- quality rules;
- access policy.

The Agent therefore reasons about concepts such as revenue, volume, conversion, merchant segment, or campaign ROI through stable business definitions rather than prompt-only schema hints.

---

### Governed analytics and NL2SQL

The model is not given unrestricted authority to invent arbitrary execution logic.

It can choose typed analytical operations such as:

- compare periods;
- inspect trends;
- break down by dimension;
- rank contributors;
- drill into anomalies;
- test hypotheses;
- run bounded code analysis.

Execution remains inside governed tools with:

- SQL parsing and validation;
- access control;
- row / result budgets;
- sandboxed Python;
- deterministic analytical operators;
- evidence snapshots.

---

### Claim → Evidence → Verification

A correct query does not guarantee a correct conclusion.

Important business claims are therefore linked to:

- source data snapshot;
- metric / semantic version;
- query or computation;
- parameters;
- observation;
- validation result.

```text
Observation
    ↓
Claim
    ↓
Evidence
    ↓
Verification
    ↓
Accept / Qualify / Reject / Replan
```

The Agent cannot treat an observed contribution as causal evidence unless the available data supports that claim.

---

## Skill Runtime

Reusable business capabilities are represented as typed Skills.

A Skill contains:

```text
skill_id
version
description
input schema
output schema
tool dependencies
permissions
tags
```

Current reference skills include:

```text
business.metric_analysis
business.attribution
business.marketing_budget
business.sales_expansion
business.monetization
runtime.verify_action
```

The runtime supports deterministic registration, lookup, routing, and permission-aware execution.

Future skill evolution is gated by offline evaluation rather than allowing production trajectories to directly rewrite executable behavior.

---

## Long-term memory

The project deliberately does not call chat history "long-term memory."

Memory is separated into:

| Memory type | Purpose |
| --- | --- |
| **Working** | Current task facts and intermediate state |
| **Episodic** | Previous trajectories and outcomes |
| **Semantic** | Stable business knowledge and definitions |
| **Procedural** | Reusable skills and verified procedures |

Memory records are versioned, task-aware, queryable, and can expire.

---

## Safety and Human-in-the-loop

Business Agents should not turn an LLM suggestion directly into an irreversible write.

The action path is:

```text
Agent Decision
      ↓
Typed Proposed Action
      ↓
Permission Check
      ↓
Tool / Token / Cost Budget
      ↓
Risk Classification
      ↓
Human Approval if Required
      ↓
Idempotent External Action
      ↓
Audit Trail
```

Financial actions are approval-gated.

The public repository intentionally keeps proprietary CRM / campaign writes in **dry-run / proposal mode**.

Implemented safety controls include:

- permission checks;
- read / write separation;
- tool allowlists;
- budget limits;
- HITL approval;
- idempotency keys;
- SQL guardrails;
- sandbox execution;
- persistent approval records;
- regression gates.

---

# BusinessAgentBench

The project includes two complementary benchmark layers.

## Hard-v1: long-horizon reliability

`BusinessAgentBench-Hard-v1` introduces controlled failure modes that a fixed four-step workflow cannot solve reliably.

It tests:

- partial observability;
- noisy evidence;
- conflicting evidence;
- tool failure / timeout;
- delayed reward;
- token and tool budget trade-offs;
- memory dependence;
- context drift;
- unsafe actions;
- multiple valid solution paths;
- retry and replanning.

Run:

```bash
make setup-training
make benchmark-hard
```

Train the small reproducible policy:

```bash
make train-hard
```

The training chain is:

```text
Expert Trajectory
      ↓
Supervised Dataset
      ↓
SFT
      ↓
Held-out Evaluation
      ↓
Failure-focused Rollouts
      ↓
Group-relative Policy Optimization
      ↓
Acceptance Gate
```

---

## RealData-v1: real public business data

`BusinessAgentBench-RealData-v1` uses official public business datasets.

### UCI Bank Marketing

Used for:

- campaign conversion;
- marketing budget reasoning;
- sales prioritization;
- funnel analysis;
- recovery and safety cases.

Verified rows:

**45,211**

### UCI Online Retail

Used for:

- transaction analytics;
- retention;
- customer value;
- monetization;
- cancellation-aware reasoning.

Verified rows:

**541,909**

### Iowa wholesale snapshot

Used for:

- governed analytics;
- multi-dimensional breakdown;
- contribution analysis;
- Price / Volume / Mix analysis;
- evidence and semantic-layer evaluation.

Curated fact rows:

**6,484,227**

RealData-v1 explicitly covers:

```text
Analytics
Attribution
Marketing Budget
Sales Expansion
Monetization
Tool Use
Recovery
Safety
```

Build the full real-data benchmark:

```bash
pip install -e '.[benchmark]'
python scripts/build_real_business_benchmark.py
```

Raw public records are downloaded to the artifact directory and are not committed to Git.

---

# Post-training and AgentRL

## Reproducible small-policy experiments

A small PyTorch Transformer policy is used to make the entire training and RL pipeline reproducible in normal CI.

It predicts the next governed Skill / Action from canonical observable task state.

This allows the repository to automatically test:

- trajectory collection;
- SFT data construction;
- supervised action learning;
- policy rollouts;
- grouped relative advantages;
- clipped policy updates;
- KL control;
- safety-preserving supervised anchors;
- held-out evaluation.

This model is an **experimental policy head**, not a claim that a tiny Transformer replaces an LLM.

---

## Real open-weight LLM path

The repository also implements a real causal-language-model policy.

Current default smoke configuration:

```text
Qwen/Qwen3-0.6B
```

The same interface can be used with larger Qwen / Llama-class models.

The evaluation path is:

```text
BusinessAgentBench State
        ↓
Governed Action Prompt
        ↓
Causal-LM Action Log Probabilities
        ↓
Tool / Skill Selection
        ↓
Environment Transition
```

Implemented:

- base-model evaluation;
- prompted evaluation;
- expert trajectory export;
- LoRA SFT;
- held-out evaluation;
- action-level GRPO-style optimization;
- post-GRPO evaluation.

Commands:

```bash
make setup-llm
make llm-dataset

python scripts/evaluate_llm_agent.py   --model Qwen/Qwen3-0.6B

make llm-sft

python scripts/evaluate_llm_agent.py   --model Qwen/Qwen3-0.6B   --adapter artifacts/models/qwen3-agent-sft

make llm-grpo
```

A separate manual self-hosted workflow is provided:

```text
.github/workflows/llm-agent.yml
```

Real open-weight LLM gain numbers are **not reported yet** because the GPU/self-hosted run has not been completed and retained.

---

# Production runtime

## PostgreSQL durable state

The production adapter persists:

- trajectory events;
- checkpoints;
- HITL approval records.

Verified in CI with a real PostgreSQL service.

Runtime APIs include:

```text
PUT  /api/v1/runtime/checkpoints/{task_id}
GET  /api/v1/runtime/checkpoints/{task_id}

POST /api/v1/approvals
GET  /api/v1/approvals/{approval_id}
POST /api/v1/approvals/{approval_id}/decision
```

---

## Redis queue and async worker

Implemented:

- Redis-backed task queue;
- in-process async queue;
- async worker;
- retry scheduling;
- bounded attempts.

Redis round trips and retry behavior are integration-tested in CI.

---

## Model routing and cost control

The runtime supports three routing tiers:

```text
FAST
STANDARD
REASONING
```

Routing can depend on:

- task complexity;
- execution risk;
- verification requirements;
- remaining token budget.

A provider-neutral Cost Ledger records:

- input tokens;
- output tokens;
- model calls;
- configured dollar cost.

No model price is silently invented: prices must be configured explicitly.

---

## Observability

Runtime metrics are emitted through OpenTelemetry.

Tracked signals include:

- task success;
- tool calls;
- policy violations;
- token usage;
- dollar cost;
- step latency.

A local stack is provided for:

```text
OpenTelemetry Collector
        ↓
Prometheus
        ↓
Grafana
```

Start it with:

```bash
docker compose up -d redis otel-collector prometheus grafana
```

Grafana:

```text
http://localhost:3000
```

---

## Canary and regression gates

Candidate policies can be blocked when they regress on:

- task success;
- policy violation rate;
- invalid action rate;
- cost.

Hard-v1 also has a dedicated acceptance gate requiring:

```text
Direct / Random remain weak
Prompt > Direct
SFT > Prompt on success
GRPO does not regress SFT success
GRPO improves average reward
GRPO reduces invalid actions
GRPO does not worsen policy violations
```

This turns Agent evaluation into a release criterion rather than a dashboard-only metric.

---

# Quick start

## Requirements

- Python **3.12+**
- Docker / Docker Compose for PostgreSQL, Redis, and observability
- GPU only for real open-weight LLM training

Install:

```bash
make setup
```

Build the existing Iowa analytical snapshot:

```bash
make data
```

Start the API:

```bash
make dev
```

Open:

```text
http://127.0.0.1:8000
```

---

## Core API examples

### Discover capabilities

```bash
curl http://127.0.0.1:8000/api/v1/capabilities
```

### Create an analytical task

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analysis-tasks   -H "Content-Type: application/json"   -d '{
    "question": "Compare July 2026 wholesale sales with June 2026 by vendor."
  }'
```

### Plan a marketing-budget task

```bash
curl -X POST http://127.0.0.1:8000/api/v1/business-tasks   -H "Content-Type: application/json"   -d '{
    "scenario": "MARKETING_BUDGET",
    "question": "Allocate the remaining budget across eligible segments.",
    "success_metrics": ["roi", "incremental_revenue"],
    "constraints": [
      {
        "name": "budget",
        "operator": "<=",
        "value": 1000000,
        "unit": "CNY"
      }
    ],
    "dry_run": true
  }'
```

---

# Development and verification

Run core tests:

```bash
make test
```

Lint:

```bash
make lint
```

Run deterministic evaluation:

```bash
make evaluation
```

Run the original trajectory flywheel:

```bash
make flywheel-smoke
```

Run Hard-v1:

```bash
make benchmark-hard
make train-hard
```

Run RealData-v1:

```bash
make benchmark-real
```

Run production integration locally:

```bash
docker compose up -d postgres redis
make setup-production
make production-test
```

---

# CI

The normal GitHub Actions workflow contains four independent jobs:

| Job | What it verifies |
| --- | --- |
| **core** | lint, 621-test core suite, hard policies, Retail benchmark, 210-case adversarial gate |
| **post-training-smoke** | trajectory, SFT, GRPO, Hard-v1 acceptance |
| **real-data-benchmark** | official Bank Marketing + Online Retail ingestion |
| **production-integration** | PostgreSQL connector + durable PostgreSQL/Redis + Docker sandbox |

Current verified snapshot:

```text
Core CI                621 passed / 18 skipped
Training CI              7 passed
Production integration   8 passed
Hard-v1 acceptance       PASS
RealData-v1              PASS
```

---

# Repository structure

```text
src/eiw/
├── domain/          persisted domain contracts
├── semantic/        versioned Semantic Layer
├── workspace/       analytical workflow and public data execution
├── business/        business scenarios and operations planner
├── runtime/         skills, memory, governance
├── benchmark/       BusinessAgentBench environments and real-data adapters
├── flywheel/        trajectory, evaluation, failure mining
├── training/        reproducible small-policy SFT / GRPO
├── llm_agent/       real causal-LM evaluation and LoRA / GRPO
├── production/      PostgreSQL, Redis, routing, cost, metrics, canary
└── app.py           FastAPI application

evaluation/
└── business_agent_bench/

semantic_packages/   versioned business semantics
scripts/             ingestion, benchmark, training, regression scripts
ops/                 OTel, Prometheus, Grafana configuration
tests/               unit, contract, integration tests
docs/                architecture and execution reports
```

---

# Technology stack

### Agent / application

- Python 3.12
- FastAPI
- Pydantic
- Supervisor–Executor runtime
- typed Skills and Tool contracts

### Data

- PostgreSQL
- DuckDB / Parquet for reproducible public-data analytics
- SQLAlchemy / Alembic
- SQLGlot
- versioned Semantic Layer

### Runtime

- Redis
- async workers
- checkpoint / resume
- sandbox execution
- RBAC / policy gates
- HITL approvals

### Evaluation / training

- PyTorch
- trajectory replay
- failure mining
- SFT
- GRPO-style AgentRL
- Transformers / PEFT for open-weight LLM path

### Observability

- OpenTelemetry
- Prometheus
- Grafana

---

# What is deliberately not claimed

This repository is designed to make the boundary between **implemented**, **verified**, and **not available publicly** explicit.

It does **not** claim:

- access to proprietary Meituan, CRM, advertising, or merchant production APIs;
- production-scale marketing-budget execution;
- causal marketing lift from observational public datasets;
- real Qwen/Llama SFT or GRPO gains before the external GPU workflow is actually run;
- production-scale throughput from CI smoke tests.

External writes in the public implementation remain dry-run or approval-gated.

---

# Design principles

1. **State over chat history**  
   Durable task state is the source of truth; prompts are temporary views.

2. **Model decides, deterministic systems execute**  
   The model selects analytical or operational actions; governed tools enforce execution boundaries.

3. **Evidence before claims**  
   Important business conclusions must be traceable to data, semantics, computations, and validation.

4. **Recovery is part of the runtime**  
   Retry, checkpoint, resume, replay, and replanning are not prompt tricks.

5. **Safety before autonomy**  
   High-risk writes require explicit permissions, budgets, idempotency, and human approval.

6. **Evaluation before self-improvement**  
   Prompt changes, Skills, SFT, or RL are promoted only after reproducible offline evaluation.

7. **Report measured results, not hoped-for results**  
   GRPO is reported as a reward/action-validity improvement because that is what the current experiment actually shows.

---

## Documentation

- [Business Intelligence & Autonomous Operations Architecture](docs/business-intelligence-autonomous-operations.md)
- [P9–P12 Execution Report](docs/P9_P12_EXECUTION_REPORT.md)
- [Demo Console](docs/DEMO.md)
- [Architecture Development Baseline](docs/architecture-development-baseline.md)
- [Core Module Design](docs/core-module-design.md)

---

## License

Apache-2.0
