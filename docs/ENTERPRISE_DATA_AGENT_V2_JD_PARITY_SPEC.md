# Enterprise Data Agent v2 — JD Parity Specification

> Status: **FROZEN**
>
> Version: **v2.0**
>
> Date: **2026-09-18**
>
> Repository: `Benjamindaoson/enterprise-data-agent`
>
> Purpose: Upgrade the current public reference implementation into a production-shaped Enterprise Data Agent whose **implemented, testable capabilities map one-to-one to the target Enterprise Data Agent / Data Intelligence Agent / ChatBI / NL2SQL role family**.
>
> This document is the implementation contract for Codex and future contributors. Where this specification conflicts with older aspirational architecture notes, this document controls the v2 upgrade scope.

---

## 0. Frozen objective

The v2 project is not a generic LLM demo and is not a pure Text-to-SQL benchmark implementation.

The target system is:

> **A governed autonomous analytics agent that turns natural-language business questions into semantically grounded, permission-aware, multi-step analysis over enterprise data; supports governed NL2SQL, typed analytical tools, trend/anomaly/attribution analysis, evidence-backed conclusions, report generation, evaluation, and end-to-end observability.**

The project must demonstrate the following end-to-end chain with real code and reproducible tests:

```text
Natural-language business question
        ↓
Intent recognition
        ↓
Business semantic resolution
        ↓
Metric / dimension / entity / time resolution
        ↓
Knowledge and metadata retrieval
        ↓
Task planning
        ↓
Supervisor-driven investigation loop
        ↓
Tool routing
   ┌──────────────┬───────────────┬────────────────┐
   │ Metric Query │ Governed NL2SQL│ Python Analysis│
   └──────────────┴───────────────┴────────────────┘
        ↓
Observation
        ↓
Hypothesis update / replan / drill-down
        ↓
Trend / anomaly / contribution / attribution
        ↓
Claim → Evidence → Verification
        ↓
Chart / dashboard / report
        ↓
Recommendation / next investigation lead
```

Cross-cutting requirements:

```text
Governance + Evaluation + Observability + Durable Runtime
```

### 0.1 What “100% JD parity” means

“100%” means **100% capability coverage**, not perfect model accuracy.

Every material capability named in the target JD must have at least one of the following concrete implementation artifacts:

- production-path code;
- integration test;
- deterministic or model-backed evaluation case;
- trace/span evidence;
- UI inspection surface;
- architecture/API contract;
- security policy test;
- reproducible demo.

A capability that exists only in README prose, a dependency list, an unused abstraction, or an old `legacy_imports/` implementation is **not counted as implemented**.

### 0.2 Truthfulness rule

The public project may claim:

- production-shaped architecture;
- enterprise-style controls;
- reproducible public-data implementation;
- measured evaluation results;
- implemented adapters and tests.

It must **not** claim:

- real enterprise customer deployment unless it happened;
- production traffic volume that was not measured;
- accuracy, latency, cost, or reliability values that were not measured;
- complete enterprise SSO, HA, K8s, or warehouse support if only interfaces exist.

No fabricated scores. No skipped test treated as passed. No “supported” claim without a code path.

---

# 1. Current baseline and preservation rules

The current repository already contains valuable foundations and they must be preserved unless this specification explicitly replaces them.

Existing assets to retain:

- versioned semantic packages;
- durable task/domain contracts;
- metric and dimension definitions;
- governed deterministic analytical operators;
- contribution and PVM analysis;
- task history, checkpoint artifacts, events, replay surfaces;
- claim → evidence → validation model;
- FastAPI product surface;
- evaluation directory and Golden Case runner;
- DuckDB + Parquet reproducible public-data path;
- PostgreSQL persistence contracts;
- report artifacts;
- current Iowa wholesale reference domain.

### 1.1 Do not regress the deterministic path

The current deterministic analytical lane is not replaced by free-form NL2SQL.

The v2 system must support **two query lanes**:

```text
                         Query Planner
                              │
              ┌───────────────┴───────────────┐
              │                               │
      Governed Metric Query             Governed NL2SQL
              │                               │
      Known KPI / routine BI          Long-tail ad-hoc query
              │                               │
      Typed semantic operators          LLM-generated SQL
              │                               │
              └───────────────┬───────────────┘
                              ↓
                       Governed Execution
                              ↓
                         Observation
```

Routing rules:

- known metrics, known dimensions, common period comparisons, contribution, PVM, variance, and routine BI should prefer the deterministic semantic lane;
- ad-hoc questions that require flexible joins, projections, filters, grouping, or uncommon combinations may use governed NL2SQL;
- either lane must produce the same provenance/evidence contract;
- neither lane may bypass policy, verification, audit, or tracing.

---

# 2. JD traceability matrix

The project is complete only when every row below has executable evidence.

| JD capability | v2 implementation artifact | Required acceptance evidence |
| --- | --- | --- |
| Enterprise Data Agent for finance/management/metrics/diagnostics | Product workflow + domain packages | End-to-end demo task |
| Natural-language understanding | Intent Resolver | Intent eval |
| Semantic parsing | Semantic Resolver | Metric/dimension/time eval |
| Metric mapping | Semantic Layer | Versioned metric definitions + tests |
| Data query | Metric lane + NL2SQL lane | Integration tests |
| Attribution / root-cause-style analysis | Contribution/PVM/variance/drill-down | Numerical reconciliation tests |
| Conclusion generation | Claim Synthesizer | Evidence-linked report |
| Task routing | Supervisor / Router | Trace + tool-choice eval |
| NL2SQL / Text2SQL | Governed NL2SQL module | Execution/result-equivalence eval |
| SQL generation | Generator | Generated candidate visible in inspector |
| SQL repair | Repair loop | Failure-injection tests |
| SQL parsing | SQLGlot AST layer | AST policy tests |
| SQL optimization / cost control | EXPLAIN/cost guard | Budget rejection tests |
| Result explanation | Result interpreter + evidence | Evidence view |
| Query security | Governance policy | Red-team cases |
| Agent task decomposition | Planner | Structured plan |
| Tool calling | Typed Tool Registry | Tool trace |
| State management | Durable runtime | Checkpoint/resume test |
| Context management | Context compiler | Context snapshot |
| Python analysis | Sandboxed typed Python tool | Resource-limit tests |
| Chart generation | Chart artifact pipeline | Artifact test |
| Report generation | Report composer | Faithfulness validation |
| Multi-step execution | Supervisor loop | Multi-step task test |
| Observability | OpenTelemetry + structured logs | Trace inspection |
| Finance/operations/supply chain/sales scenarios | Domain packages | Cross-domain eval |
| NL2SQL evaluation | Eval suite | Measured report |
| Metric QA evaluation | Eval suite | Measured report |
| Attribution evaluation | Eval suite | Measured report |
| Report evaluation | Eval suite | Faithfulness metrics |
| Accuracy / recall / consistency / factuality / stability / latency | Eval harness | Versioned scorecard |
| Data-source access | Connector interface | PostgreSQL + DuckDB adapters |
| Knowledge base | RAG/metadata retrieval | Retrieval eval |
| Prompt templates | Versioned prompt registry | Prompt/version in trace |
| Tool plugins | Typed Tool Registry | Registered capabilities |
| Access control | RBAC/row policy/masking | Policy tests |
| Log monitoring | OTel + structured logs | Dashboard/trace |
| Evaluation framework | Versioned eval runner | CI regression gate |
| Multi-domain replication | Semantic package contract | ≥3 domains without runtime fork |

---

# 3. Target architecture

```text
┌────────────────────────────────────────────────────────────────────┐
│                         Product Surfaces                            │
│ Cockpit | Ask Data | Investigation | SQL Inspector | Eval | Trace │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Agent / Analytical Intelligence                  │
│ Intent Resolver | Semantic Resolver | Planner | Supervisor         │
│ Router | Hypothesis Manager | Claim Synthesizer                    │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                       Durable Agent Runtime                         │
│ State | Context | Checkpoint | Budget | Retry | Resume | Events    │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Tool Registry                               │
│ Metric | NL2SQL | Knowledge | Python | Trend | Anomaly | PVM      │
│ Contribution | Variance | Drilldown | Chart | Report               │
└────────────────────────────────────────────────────────────────────┘
                              │
             ┌────────────────┼─────────────────┐
             ▼                ▼                 ▼
       Semantic Layer    Knowledge/RAG      NL2SQL Engine
             │                │                 │
             │                │         Generate → AST → Policy
             │                │          → EXPLAIN → Execute
             │                │          → Validate → Repair
             └────────────────┼─────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Governed Data Execution                          │
│ DuckDB Adapter | PostgreSQL Adapter | read-only | limits | audit   │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Evidence / Verification                         │
│ Observation | Claim | Evidence | Validation | Provenance           │
└────────────────────────────────────────────────────────────────────┘

Cross-cutting:
Governance | OpenTelemetry | Evaluation | Security | Prompt Registry
```

---

# 4. Target repository structure

The exact filenames may evolve, but the responsibility boundaries are frozen.

```text
src/eiw/
├── agent/
│   ├── intent.py
│   ├── semantic_resolver.py
│   ├── planner.py
│   ├── supervisor.py
│   ├── router.py
│   ├── hypothesis.py
│   └── synthesizer.py
│
├── runtime/
│   ├── state.py
│   ├── context.py
│   ├── checkpoint.py
│   ├── recovery.py
│   ├── budget.py
│   └── events.py
│
├── semantic/
│   ├── package.py
│   ├── metrics.py
│   ├── dimensions.py
│   ├── glossary.py
│   ├── metadata.py
│   └── resolver.py
│
├── nl2sql/
│   ├── schema_retriever.py
│   ├── schema_linker.py
│   ├── example_retriever.py
│   ├── planner.py
│   ├── generator.py
│   ├── parser.py
│   ├── policy.py
│   ├── semantic_validator.py
│   ├── cost_guard.py
│   ├── executor.py
│   ├── result_validator.py
│   └── repair.py
│
├── knowledge/
│   ├── indexer.py
│   ├── retriever.py
│   └── contracts.py
│
├── analytics/
│   ├── trend.py
│   ├── period_compare.py
│   ├── contribution.py
│   ├── pvm.py
│   ├── variance.py
│   ├── anomaly.py
│   └── drilldown.py
│
├── tools/
│   ├── registry.py
│   ├── metric.py
│   ├── sql.py
│   ├── knowledge.py
│   ├── python.py
│   ├── chart.py
│   └── report.py
│
├── governance/
│   ├── identity.py
│   ├── rbac.py
│   ├── policy.py
│   ├── masking.py
│   └── audit.py
│
├── evidence/
│   ├── observation.py
│   ├── claim.py
│   ├── provenance.py
│   └── verifier.py
│
├── observability/
│   ├── tracing.py
│   ├── metrics.py
│   └── logging.py
│
├── evaluation/
│   ├── runner.py
│   ├── graders.py
│   ├── metrics.py
│   └── regression.py
│
└── connectors/
    ├── base.py
    ├── duckdb.py
    └── postgres.py

semantic_packages/
├── iowa_liquor_wholesale/
├── finance/
├── sales_operations/
└── supply_chain/

knowledge_base/
evaluation/
tests/
docs/
```

---

# 5. P0 — JD parity core

> **P0 is the minimum acceptable v2.**
>
> P0 is intentionally larger than a conventional MVP. P0 means the project can truthfully demonstrate every core technical capability required by the target JD.

No P1 work should be used to hide an unfinished P0 capability.

## P0.1 Real model-provider path

### Required implementation

Introduce a formal model provider contract and one real model-backed implementation.

The deterministic provider remains available for reproducible tests, but the product must have a real provider path for:

- intent resolution;
- semantic interpretation;
- plan generation;
- tool selection;
- NL2SQL generation;
- repair;
- claim/report synthesis.

Requirements:

- provider interface must be independent of business-domain models;
- provider response must use structured output / typed parsing where appropriate;
- provider/model/prompt version must be traceable;
- timeouts, retry policy, and failure classification must be explicit;
- no silent fallback from failed real-provider execution to deterministic “success”.

### Acceptance criteria

- [ ] `EIW_MODEL_PROVIDER=deterministic` passes offline tests.
- [ ] A real provider mode executes at least one complete multi-step task.
- [ ] Provider timeout produces a typed failure, not an invented answer.
- [ ] Provider/model/prompt version is present in task trace.
- [ ] Unit tests cover malformed structured output.
- [ ] Integration test proves deterministic and real-provider paths share the same domain contracts.

---

## P0.2 Intent + semantic resolution

### Required implementation

Replace regex-only understanding as the primary model-backed path.

Resolved intent must include at minimum:

- objective;
- requested output;
- metric candidates and selected metric versions;
- dimensions;
- entities/filters;
- time range;
- comparison baseline;
- desired analysis type;
- ambiguity state;
- unresolved assumptions.

Semantic resolution must use the semantic package, not model memory, as the source of truth.

Ambiguity must fail into clarification when different interpretations materially change the result.

### Acceptance criteria

- [ ] Natural-language aliases map to versioned metrics.
- [ ] Time expressions resolve to absolute intervals.
- [ ] Metric ambiguity triggers clarification.
- [ ] Unsupported metrics return a typed unsupported-semantic result.
- [ ] User without access cannot resolve a forbidden metric into executable context.
- [ ] At least 50 intent/semantic cases exist in P0 evaluation.
- [ ] Paraphrases of the same request are checked for semantic consistency.

---

## P0.3 Semantic Layer v2

### Required implementation

Each metric definition must support:

- id and version;
- name and aliases;
- description;
- formula / semantic expression;
- unit;
- valid grains;
- supported dimensions;
- allowed join paths;
- source tables/columns;
- time semantics;
- availability/freshness constraints;
- owner;
- business rules;
- data classification;
- access policy tags;
- lineage references.

Dimension definitions must support:

- id and aliases;
- source mapping;
- grain;
- hierarchy where relevant;
- access tags;
- join/cardinality rules.

### Acceptance criteria

- [ ] Semantic packages validate against a typed schema.
- [ ] Invalid metric references fail CI.
- [ ] Invalid dimension/join references fail CI.
- [ ] Metric versions are included in evidence.
- [ ] Semantic version is included in trace and report provenance.
- [ ] No model path is allowed to invent an unregistered authoritative metric formula.

---

## P0.4 Governed NL2SQL engine

This is a mandatory first-class v2 capability.

### Required pipeline

```text
ResolvedBusinessIntent
  → relevant schema retrieval
  → metric/dimension context
  → optional example retrieval
  → logical query plan
  → candidate SQL generation
  → SQLGlot parse / AST
  → syntax + statement validation
  → table/column policy validation
  → semantic validation
  → join/cardinality validation
  → row/tenant policy injection or enforcement
  → complexity / budget check
  → EXPLAIN where supported
  → read-only execution
  → result validation
  → bounded repair loop
  → normalized execution result
```

### Mandatory SQL safety rules

At minimum:

- SELECT-only on analytical query path;
- block INSERT/UPDATE/DELETE/MERGE;
- block DDL;
- table allowlist;
- column allowlist / denylist;
- sensitive-column restrictions;
- multi-statement rejection;
- unsafe function restrictions where applicable;
- row limit policy;
- timeout/query budget;
- cross-tenant access prevention;
- unauthorized join prevention;
- comments/UNION/subquery bypass tests;
- read-only connection/session.

### SQL repair classification

Repair must distinguish at minimum:

- syntax error;
- unknown table;
- unknown column;
- invalid alias;
- invalid join;
- aggregation/grain error;
- semantic mismatch;
- permission denial;
- timeout/budget failure;
- empty-but-unexpected result;
- result-shape mismatch.

Do not repair policy denials into bypasses.

### Acceptance criteria

- [ ] SQLGlot is called in the active NL2SQL path.
- [ ] Candidate SQL and validated SQL are separately traceable.
- [ ] DML/DDL/multi-statement attacks are rejected before execution.
- [ ] Unauthorized table/column queries are rejected.
- [ ] At least one recoverable SQL failure is successfully repaired.
- [ ] Policy denial is never sent to repair as a prompt to evade the policy.
- [ ] Repair attempts are bounded.
- [ ] Execution result includes SQL hash, rows, latency, source id/version, and warnings.
- [ ] P0 NL2SQL evaluation has at least 75 cases covering generation, semantics, security, and repair.
- [ ] Eval measures execution success and result equivalence, not only exact SQL text.

---

## P0.5 Dual-lane query planner

### Required implementation

The planner must choose between:

1. deterministic metric/operator lane;
2. governed NL2SQL lane.

Decision factors may include:

- whether a supported metric/operator can satisfy the request;
- join complexity;
- ad-hoc projection/filter need;
- unsupported combinations;
- required flexibility;
- policy constraints.

### Acceptance criteria

- [ ] Routine metric query uses deterministic lane.
- [ ] Long-tail query can select NL2SQL.
- [ ] Both lanes emit common Observation/Evidence contracts.
- [ ] Lane decision is captured in trace.
- [ ] Evaluation includes tool/lane selection cases.

---

## P0.6 Supervisor-driven multi-step investigation

### Required implementation

A real runtime loop must exist:

```text
State
  → decide next analytical action
  → execute governed tool
  → record observation
  → update hypothesis
  → verify
  → replan / drill down / clarify / synthesize / stop
```

The model may decide **what to investigate next**.

The runtime decides:

- whether the action is permitted;
- whether budget remains;
- whether the tool call is valid;
- whether retry is allowed;
- whether state can be persisted/resumed;
- whether the output is accepted into evidence.

### Required state objects

- AnalysisTask;
- ResolvedBusinessIntent;
- AnalysisPlan;
- ContextPackage;
- Hypothesis[];
- ToolExecution[];
- Observation[];
- Claim[];
- Evidence[];
- ValidationResult[];
- Budget;
- Checkpoint;
- terminal status.

### Acceptance criteria

- [ ] At least one evaluation task requires ≥3 analytical steps.
- [ ] The second/third step depends on a prior observation.
- [ ] Runtime can stop on budget exhaustion.
- [ ] Runtime can request clarification.
- [ ] Runtime can resume a persisted task without duplicating accepted evidence.
- [ ] No raw private chain-of-thought is persisted or exposed.
- [ ] A failed tool execution is typed and visible in timeline/trace.

---

## P0.7 Tool Registry and analytical tools

### Required tool set

P0 must expose typed tools for:

- `metric_query`
- `nl2sql_query`
- `metric_explain`
- `knowledge_search`
- `period_compare`
- `trend_analysis`
- `contribution_analysis`
- `pvm_analysis`
- `variance_analysis`
- `drilldown_analysis`
- `python_analysis`
- `chart_generate`
- `report_generate`

### Python analysis requirements

The Python capability must not be unrestricted host execution.

At minimum:

- bounded execution interface;
- typed input artifact;
- timeout;
- memory/resource limit where feasible;
- no arbitrary network by default;
- controlled filesystem/artifact path;
- captured stdout/error metadata;
- trace span;
- deterministic functions preferred for routine calculations.

### Acceptance criteria

- [ ] Tool schemas are typed.
- [ ] Tool registry exposes only policy-permitted tools.
- [ ] Invalid tool arguments fail before execution.
- [ ] Python timeout test exists.
- [ ] Tool outputs are normalized into Observation candidates.
- [ ] Tool calls are represented in OpenTelemetry spans.

---

## P0.8 Knowledge base / RAG / metadata retrieval

### Required knowledge sources

The project must index and retrieve:

- business glossary;
- metric definitions;
- data dictionary;
- table/column documentation;
- lineage notes;
- business rules;
- approved SQL examples;
- analyst playbooks / FAQ where available.

Retrieval results must include source identity/version.

The model must not treat retrieved text as an authorization source; permissions come from governance.

### Acceptance criteria

- [ ] Knowledge retrieval is a real callable tool.
- [ ] Retrieval source references are included in trace.
- [ ] Metric definition question can be answered from the authoritative semantic/knowledge asset.
- [ ] Retrieval eval contains at least 25 cases.
- [ ] Prompt injection inside retrieved text cannot grant additional permissions.

---

## P0.9 Governance, RBAC, row/column policy, and audit

### Required personas

At minimum create four public demo personas:

- CFO;
- Finance Analyst;
- Regional Manager;
- Sales Manager.

Policy model must demonstrate different visibility for:

- metrics;
- dimensions;
- regions/business units;
- sensitive fields;
- export/report actions where applicable.

### Mandatory policy checkpoints

1. task creation;
2. context compilation;
3. knowledge visibility;
4. tool availability;
5. SQL AST validation;
6. source execution;
7. evidence capture;
8. artifact read/export;
9. trace access.

### Required security tests

At minimum:

- DDL request;
- DML request;
- multi-statement request;
- unauthorized metric;
- unauthorized table;
- sensitive column;
- wrong-region request;
- cross-tenant request;
- prompt-injection attempt;
- SQL comment bypass;
- UNION bypass;
- nested subquery bypass;
- tool argument privilege escalation.

### Acceptance criteria

- [ ] All policy-denial tests fail closed.
- [ ] Unauthorized result data is never persisted to evidence before denial.
- [ ] Security/audit events are distinct from model prompts.
- [ ] Audit record contains actor/policy/action/result/correlation id.
- [ ] Security suite is part of CI.

---

## P0.10 Enterprise data connectors

### Required implementation

Keep DuckDB as the reproducible public reference data path.

Add PostgreSQL as a first-class analytical source adapter, not only metadata persistence.

Connector contract must expose:

- source description;
- schema introspection;
- read-only session;
- query execution;
- cancellation/timeout;
- freshness/version metadata;
- source identity;
- execution metadata.

### Acceptance criteria

- [ ] Same logical query contract can run on DuckDB and PostgreSQL where dialect permits.
- [ ] PostgreSQL analytical path has an integration test.
- [ ] SQL dialect is explicit.
- [ ] Read-only enforcement is tested.
- [ ] Query timeout/cancel behavior is tested or explicitly marked unsupported by adapter.

---

## P0.11 Enterprise business domains

P0 must no longer be a single-domain proof.

Required domain packages:

1. `iowa_liquor_wholesale` — retained reproducible public reference;
2. `finance`;
3. `sales_operations`;
4. `supply_chain`.

The finance/sales/supply-chain demo datasets may be synthetic or public, but must be clearly labeled.

### Finance minimum metrics

- revenue;
- gross profit;
- gross margin rate;
- operating expense;
- operating profit;
- budget variance.

### Sales minimum metrics

- sales/revenue;
- orders;
- average selling price;
- customer count;
- region/channel/product contribution.

### Supply chain minimum metrics

- inventory;
- inventory turnover;
- stockout;
- lead time;
- fill rate;
- supplier on-time/in-full or equivalent.

### Acceptance criteria

- [ ] Each domain has versioned semantic package.
- [ ] Core runtime code is not forked per domain.
- [ ] At least one end-to-end task passes per domain.
- [ ] At least one cross-domain ambiguity case is tested.
- [ ] Domain-specific unsupported claims return explicit limits.

---

## P0.12 Attribution / diagnostic analytics

The JD uses “归因分析”, but the project must distinguish descriptive attribution from causal inference.

Required analytical capabilities:

- period comparison;
- trend;
- contribution decomposition;
- PVM;
- variance analysis;
- drill-down;
- anomaly detection or anomaly scoring;
- reconciliation.

Language rule:

> Contribution/decomposition/association must not be presented as proven causation without an actual causal identification design.

### Acceptance criteria

- [ ] Contribution components reconcile to the total within declared tolerance.
- [ ] PVM components reconcile to total change within declared tolerance.
- [ ] Budget-vs-actual variance example is implemented.
- [ ] No-dominant-driver case can abstain from inventing a root cause.
- [ ] Causal-language validator downgrades/blocks unsupported causal claims.

---

## P0.13 Evidence-backed answer generation

Required chain:

```text
Execution
  → Observation
  → Evidence Candidate
  → Validation
  → Claim
  → Report Artifact
```

Every material factual claim in the final report must be traceable to:

- metric/version;
- semantic/context version;
- source/data snapshot;
- query/computation reference;
- result hash or artifact identity;
- validation status.

### Acceptance criteria

- [ ] Claim without supporting evidence cannot be marked VERIFIED.
- [ ] Report cannot introduce a new unsupported factual number.
- [ ] Evidence view can navigate claim → observation → query/computation → source/version.
- [ ] Report faithfulness validation runs after report generation.
- [ ] Unsupported statement injection test fails.

---

## P0.14 OpenTelemetry observability

OpenTelemetry must be implemented in the active v2 path, not only declared as a dependency.

### Required top-level trace

```text
data_agent.task
├── intent.resolve
├── semantic.resolve
│   ├── metric.retrieve
│   ├── schema.retrieve
│   └── knowledge.retrieve
├── plan.create
├── investigation.step
│   ├── tool.select
│   ├── nl2sql.generate
│   ├── sql.parse
│   ├── sql.policy_validate
│   ├── sql.semantic_validate
│   ├── sql.explain
│   ├── sql.execute
│   └── result.validate
├── hypothesis.update
├── claim.synthesize
├── claim.verify
└── report.generate
```

### Required span attributes where applicable

- task_id;
- domain_id;
- model/provider;
- prompt version;
- tool name;
- metric ids;
- dimension ids;
- SQL hash, never secrets;
- query lane;
- row count;
- latency;
- retry count;
- repair count;
- token usage;
- validation status;
- error category;
- policy decision;
- correlation id.

Do not put private chain-of-thought, credentials, or raw sensitive records into spans.

### Acceptance criteria

- [ ] Active v2 request emits a root trace.
- [ ] LLM/tool/SQL/verification steps are visible as child spans.
- [ ] Trace context propagates through tool execution.
- [ ] Error span contains typed category.
- [ ] OTel can export via OTLP.
- [ ] A local observability setup can visualize traces; Grafana/Tempo is preferred.
- [ ] README/docs show how to run observability locally.

---

## P0.15 Evaluation framework

P0 evaluation is a product requirement, not a final polish step.

### Required evaluation suites

1. Intent resolution;
2. metric matching;
3. dimension/entity/time resolution;
4. knowledge retrieval;
5. tool/lane selection;
6. NL2SQL generation/execution;
7. SQL repair;
8. query security;
9. contribution/PVM/variance;
10. Agent task completion;
11. report factuality/evidence coverage;
12. paraphrase stability;
13. latency/cost telemetry.

### Required metrics

At minimum:

- intent accuracy;
- metric top-1 accuracy / recall where applicable;
- dimension accuracy;
- time resolution accuracy;
- retrieval recall/relevance;
- SQL syntax validity;
- SQL execution success;
- result equivalence;
- semantic correctness;
- repair success rate;
- policy-violation escape rate;
- task completion rate;
- tool-selection accuracy;
- evidence coverage;
- unsupported factual claim rate;
- paraphrase consistency;
- p50/p95 latency;
- tokens/cost per task when model-backed.

### P0 evaluation size

Minimum **200 versioned cases total**, with explicit tags and domain distribution.

Do not require every case to call a paid model in routine CI. Split:

- deterministic/offline CI suite;
- model-backed benchmark suite;
- security suite;
- performance suite.

### Acceptance criteria

- [ ] Eval dataset is versioned.
- [ ] Every result records provider/model/prompt/semantic/data versions.
- [ ] Scorecard is generated from measured runs.
- [ ] Regression comparison against a prior run is supported.
- [ ] No score is hard-coded into README.
- [ ] CI fails on deterministic/security regressions.
- [ ] Model-backed score thresholds are configured as gates only after baseline measurement.

---

## P0.16 Product/UI inspection surfaces

P0 UI must make the engineering system inspectable.

Required surfaces:

1. Management Cockpit;
2. Ask Data;
3. Investigation Workspace;
4. SQL / Execution Inspector;
5. Evidence Explorer;
6. Evaluation Dashboard;
7. Trace / Observability entry point.

### SQL Inspector must show

- query lane;
- logical plan if available;
- candidate SQL;
- validated/executed SQL;
- policy checks;
- SQLGlot/AST validation summary;
- EXPLAIN/cost summary where available;
- repair history;
- execution result metadata.

### Investigation Workspace must show

- resolved intent;
- semantic context;
- plan;
- hypotheses;
- steps;
- tools;
- observations;
- validations;
- claims;
- limitations.

### Acceptance criteria

- [ ] UI never exposes credentials or private chain-of-thought.
- [ ] A user can distinguish fact vs inference vs recommendation.
- [ ] A user can inspect why a query was denied.
- [ ] A user can navigate from final claim to evidence.
- [ ] Evaluation dashboard uses measured run artifacts.

---

# 6. P1 — differentiation and stronger enterprise evidence

> P1 is not required to claim JD capability coverage, but it should make the project materially stronger in interviews and closer to a pilot-ready enterprise product.

## P1.1 Proactive insight / management cockpit

Implement a watcher that can create analysis tasks from data changes rather than waiting for a chat question.

Pipeline:

```text
Data refresh
  → metric snapshot
  → change/anomaly detection
  → materiality policy
  → auto-create analysis task
  → investigation
  → evidence verification
  → insight card
```

Acceptance:

- [ ] At least one automatic anomaly/variance task is generated.
- [ ] Insight card links to the full investigation.
- [ ] False-positive / below-materiality examples can be suppressed.

---

## P1.2 Richer anomaly and diagnostic tools

Add:

- robust z-score / seasonal baseline where appropriate;
- change-point or rolling-baseline anomaly;
- reconciliation;
- sensitivity analysis;
- mix-shift decomposition;
- driver ranking with confidence/limitations.

Acceptance:

- [ ] Controlled anomaly fixtures exist.
- [ ] Missing-data scenario does not produce fake anomaly certainty.
- [ ] Driver ranking includes limitations.

---

## P1.3 Stronger RAG and schema linking

Add:

- hybrid retrieval;
- metadata graph relationships;
- approved SQL example retrieval;
- schema-link confidence;
- retrieval caching;
- hard-negative evaluation.

Acceptance:

- [ ] Large-schema simulation is available.
- [ ] Irrelevant-schema retrieval is measured.
- [ ] Retrieval output remains permission-filtered.

---

## P1.4 Production-shaped identity

Add OIDC/JWT adapter and resource-level authorization.

Acceptance:

- [ ] Trusted identity is created server-side.
- [ ] Client cannot self-assert arbitrary roles.
- [ ] Object-level read checks cover tasks/evidence/artifacts/traces.

---

## P1.5 Deployment hardening

Add:

- Docker image;
- Docker Compose full stack;
- CI workflow;
- migrations;
- health/readiness endpoints;
- structured config;
- secrets via environment/provider;
- optional Redis only if a real need exists.

Kubernetes is not required merely to satisfy the JD.

Acceptance:

- [ ] One-command local stack.
- [ ] Clean database migration from empty state.
- [ ] CI runs lint/type/test/security/eval-fast.
- [ ] No secret committed.

---

## P1.6 Performance and cost engineering

Measure:

- LLM latency;
- schema retrieval latency;
- SQL execution latency;
- total task p50/p95;
- token usage;
- repair overhead;
- cache hit rate.

Add bounded caching where correct:

- semantic assets;
- schema metadata;
- retrieved examples;
- repeated deterministic metric queries where data version is fixed.

Acceptance:

- [ ] Performance report is generated from measurement.
- [ ] Cache keys include semantic/data versions where required.
- [ ] Caching cannot leak cross-tenant data.

---

## P1.7 Evaluation growth

Expand evaluation to **≥500 cases** across all domains and failure modes.

Add:

- adversarial paraphrases;
- ambiguous business terms;
- stale schema;
- wrong joins;
- permission conflict;
- malformed tool output;
- LLM refusal/malformed JSON;
- timeout/retry cases;
- large-result protection.

---

# 7. P2 — platformization and scale proof

> P2 is optional for the job-targeting objective. It exists to prove deeper platform engineering if time permits.

## P2.1 Async/distributed execution

Introduce an asynchronous worker/queue only after a measured need.

Potential targets:

- long-running analysis jobs;
- concurrent tasks;
- cancel/resume across process boundaries;
- worker failure recovery.

Do not adopt Temporal/Celery/Kafka merely for résumé keywords.

Acceptance:

- [ ] Architecture decision record explains why the component is needed.
- [ ] Worker restart recovery test exists.
- [ ] Idempotency is preserved.

---

## P2.2 Warehouse adapters

Optional adapters:

- Snowflake;
- BigQuery;
- Databricks SQL.

Acceptance:

- [ ] Adapter conforms to the same connector contract.
- [ ] Dialect-specific SQL validation exists.
- [ ] No business logic forks by warehouse.

---

## P2.3 Semantic governance lifecycle

Add:

- metric proposal/review;
- version promotion;
- deprecation;
- lineage diff;
- semantic regression tests;
- owner approval metadata.

---

## P2.4 Advanced evaluation and red-team

Add:

- model/provider A/B;
- prompt-version A/B;
- cross-model regression;
- larger adversarial security set;
- benchmark against baseline NL2SQL systems where licensing permits.

---

## P2.5 Scale testing

Measure rather than claim:

- concurrent tasks;
- database load;
- trace volume;
- task latency under load;
- queue depth if async runtime exists.

A public report must state the actual test environment.

---

# 8. Frozen implementation order

Codex must implement in the order below unless a dependency requires a small local deviation.

## Phase 0A — contracts and traceability

1. Add this specification.
2. Add JD traceability status document.
3. Add typed provider, tool, connector, policy, and evaluation contracts.
4. Add version fields where missing.
5. Preserve existing tests.

**Exit gate:** old product still runs and new contracts compile/test.

## Phase 0B — observability foundation

1. Active OTel setup.
2. Root task trace.
3. Tool/SQL spans.
4. structured logs + correlation id.

**Exit gate:** current deterministic path produces a usable trace before model orchestration is expanded.

## Phase 0C — semantic v2 + knowledge

1. Semantic schema expansion.
2. Finance/sales/supply-chain packages.
3. Knowledge indexing/retrieval.
4. semantic/knowledge tests.

**Exit gate:** authoritative metric resolution and RAG work without NL2SQL.

## Phase 0D — governed NL2SQL

1. schema retrieval/linking;
2. logical plan;
3. generator;
4. SQLGlot parse;
5. policy;
6. semantic/join validation;
7. cost guard/EXPLAIN;
8. execution;
9. result validation;
10. repair.

**Exit gate:** NL2SQL integration + security + repair suites pass.

## Phase 0E — real Supervisor loop

1. real provider adapter;
2. intent resolver;
3. planner/router;
4. supervisor state machine;
5. hypothesis update;
6. checkpoint/resume;
7. final synthesis.

**Exit gate:** ≥3-step model-backed investigation completes with trace/evidence.

## Phase 0F — analytical tools + governance

1. variance;
2. anomaly;
3. drilldown;
4. Python tool sandbox;
5. RBAC/row/column policy;
6. audit.

**Exit gate:** security red-team and numerical reconciliation tests pass.

## Phase 0G — evaluation

1. 200-case P0 dataset;
2. offline suite;
3. model-backed suite;
4. security suite;
5. scorecard;
6. regression compare.

**Exit gate:** measured report generated; no fabricated metrics.

## Phase 0H — UI evidence surfaces

1. SQL Inspector;
2. enhanced Investigation;
3. Evidence Explorer;
4. Eval Dashboard;
5. trace link;
6. management cockpit.

**Exit gate:** interviewer can inspect the system without reading source first.

---

# 9. Acceptance gates for “P0 complete”

P0 is complete only when **all** of the following are true.

## Functional

- [ ] Natural-language question can trigger real model-backed intent resolution.
- [ ] Semantic Layer is the authoritative metric source.
- [ ] Deterministic metric lane works.
- [ ] Governed NL2SQL lane works.
- [ ] SQL repair works for a controlled recoverable error.
- [ ] Multi-step Supervisor loop works.
- [ ] Knowledge retrieval works.
- [ ] Trend, contribution, PVM, variance, drill-down, and anomaly path exist.
- [ ] Python analysis tool is bounded.
- [ ] Report is evidence-backed.
- [ ] Four domain packages exist.

## Security

- [ ] SELECT-only enforcement.
- [ ] DDL/DML blocked.
- [ ] table/column policy.
- [ ] row/region/tenant restriction.
- [ ] prompt-injection cannot grant access.
- [ ] bypass suite passes.
- [ ] read-only data connection.

## Runtime

- [ ] persisted task state.
- [ ] checkpoint.
- [ ] resume.
- [ ] bounded retry.
- [ ] bounded SQL repair.
- [ ] budget enforcement.
- [ ] typed failure categories.

## Observability

- [ ] OpenTelemetry active in current code.
- [ ] root task span.
- [ ] LLM/tool/SQL/validation child spans.
- [ ] OTLP export.
- [ ] correlation id across logs/events/trace.

## Evaluation

- [ ] ≥200 P0 cases.
- [ ] NL2SQL execution/result-equivalence scoring.
- [ ] semantic evaluation.
- [ ] security evaluation.
- [ ] attribution reconciliation.
- [ ] report factuality/evidence coverage.
- [ ] paraphrase stability.
- [ ] measured latency/token metrics for model-backed run.

## Product evidence

- [ ] Ask Data.
- [ ] Investigation.
- [ ] SQL Inspector.
- [ ] Evidence Explorer.
- [ ] Evaluation Dashboard.
- [ ] Trace entry.
- [ ] Cockpit.

## Truthfulness

- [ ] README separates “implemented” from “planned”.
- [ ] No unused dependency is described as an implemented capability.
- [ ] No legacy-only feature is described as active v2 functionality.
- [ ] No unmeasured performance/accuracy claim.
- [ ] No real-enterprise-deployment claim without evidence.

---

# 10. Test plan

The following test categories are mandatory.

## Unit tests

- semantic package validation;
- metric resolution;
- time resolution;
- SQL AST rules;
- policy decisions;
- result validators;
- reconciliation math;
- report faithfulness rules;
- budget logic.

## Integration tests

- DuckDB query path;
- PostgreSQL analytical query path;
- provider adapter;
- NL2SQL generate → validate → execute;
- repair loop;
- knowledge retrieval;
- OTel span generation;
- task checkpoint/resume.

## Security tests

- DDL/DML;
- multi-statement;
- union bypass;
- comment bypass;
- nested subquery;
- unauthorized metric;
- unauthorized table/column;
- tenant/region leak;
- prompt injection;
- tool argument escalation.

## End-to-end tests

At minimum:

1. Finance margin decline investigation.
2. Sales regional decline investigation.
3. Supply-chain stockout/lead-time investigation.
4. Long-tail NL2SQL ad-hoc question.
5. Clarification-required ambiguity.
6. Policy denial.
7. Recoverable SQL error + repair.
8. No-dominant-driver / causal-abstention case.

---

# 11. Evaluation case taxonomy

Every case must declare tags.

Suggested tags:

```text
domain:
  finance
  sales
  supply_chain
  iowa_reference

capability:
  intent
  semantic
  rag
  nl2sql
  repair
  contribution
  pvm
  variance
  anomaly
  report
  security
  runtime

difficulty:
  simple
  multi_table
  ambiguous
  long_horizon
  adversarial

failure_mode:
  unknown_metric
  stale_data
  bad_join
  permission_denied
  empty_result
  syntax_error
  timeout
  malformed_model_output
  unsupported_causality
```

Evaluation artifacts must include:

- case id;
- input;
- expected structured target;
- allowed equivalence where exact text is not required;
- data snapshot;
- semantic version;
- model/provider;
- prompt version;
- outcome;
- error/failure classification;
- timing/cost where applicable.

---

# 12. Coding rules for Codex

These rules are part of the specification.

1. **Do not rewrite the project into a framework demo.** Domain contracts remain framework-independent.
2. **Do not delete the deterministic semantic lane.**
3. **Do not allow the LLM to directly authorize itself.**
4. **Do not rely on prompt-only SQL safety.**
5. **Do not execute raw model Python on the host.**
6. **Do not persist private chain-of-thought.**
7. **Do not expose secrets or sensitive rows in traces.**
8. **Do not silently fallback from a failed model call to fabricated deterministic success.**
9. **Do not treat “query executed” as “business answer correct”.**
10. **Do not call descriptive contribution causal proof.**
11. **Do not mark a work item complete because a class/interface exists.**
12. **Do not fabricate benchmark results.**
13. **Do not treat skipped tests as passes.**
14. **Every P0 work item must have a test or measured acceptance artifact.**
15. **Prefer typed inputs/outputs and deterministic validators around model decisions.**
16. **All external effects must have explicit timeout and failure behavior.**
17. **Security paths fail closed.**
18. **Evidence/provenance must be created by the execution/verification pipeline, not arbitrary client input.**

---

# 13. Definition of Done for each Codex task

A Codex task is not complete until it includes:

- implementation;
- tests;
- documentation update where user-facing;
- migration/config update where needed;
- relevant OTel span or explicit reason no span is needed;
- relevant eval case where capability-facing;
- failure behavior;
- no new lint/type/test regression.

Task completion report must state:

```text
Files changed:
Tests added/updated:
Commands run:
Measured result:
Known limitations:
JD capability covered:
```

If a command could not be run, say so.

---

# 14. Required top-level documentation after P0

By P0 completion the repository must contain:

- `README.md` — recruiter/interviewer-facing overview;
- this JD parity specification;
- architecture document;
- semantic-layer guide;
- governed NL2SQL design;
- security model;
- evaluation methodology;
- observability guide;
- P0 completion report;
- measured evaluation report;
- known limitations.

README must have a short “Implemented vs Planned” table.

---

# 15. Interview demo scenario

The flagship demo should be a finance/operations investigation rather than a trivial single-table query.

Example:

> **“Why did South China gross margin fall in Q2, which products and channels contributed most, and is the change large enough to investigate?”**

Expected trace:

```text
1. Resolve Gross Margin metric and fiscal Q2.
2. Check regional permission.
3. Establish Q2 vs comparison baseline.
4. Run deterministic margin query.
5. Detect material decline.
6. Drill down by product.
7. Drill down by channel.
8. Run contribution / variance analysis.
9. Use NL2SQL for a long-tail supporting question if needed.
10. Validate totals and coverage.
11. Create qualified claims.
12. Produce chart/report.
13. Link every material claim to evidence.
```

The demo must visibly show:

- semantic metric definition;
- plan;
- tool choices;
- SQL or deterministic query path;
- policy checks;
- trace;
- evidence;
- limitations;
- report.

A second demo must show an explicit security denial.

A third demo must show a recoverable NL2SQL error and bounded repair.

---

# 16. Final target positioning

The final project should be describable truthfully as:

> **Enterprise Data Agent — a governed autonomous analytics system for semantic metric reasoning, NL2SQL, multi-step investigation, business diagnostics, evidence-backed reporting, evaluation, and observability.**

It should support interview discussion across:

- Agent architecture;
- LLM application engineering;
- NL2SQL / Text2SQL;
- Semantic Layer;
- enterprise metadata;
- RAG;
- SQL parsing and safety;
- Agent runtime;
- tool calling;
- state/context management;
- business analytics;
- contribution / PVM / variance;
- evaluation;
- security/governance;
- OpenTelemetry;
- backend/API;
- deployment hardening.

The architecture thesis remains:

> **The model decides what to analyze next; typed contracts, semantic rules, policy, deterministic tools, and verifiers decide what is allowed and what counts as evidence.**

---

# 17. Frozen priority summary

## P0 — required for JD parity

- real LLM/provider path;
- intent/semantic resolution;
- Semantic Layer v2;
- governed NL2SQL;
- SQLGlot AST/security;
- SQL repair;
- dual query lane;
- Supervisor multi-step loop;
- typed tool registry;
- bounded Python analysis;
- RAG/knowledge;
- RBAC/row/column policy;
- DuckDB + PostgreSQL analytical adapters;
- finance/sales/supply-chain domains;
- trend/contribution/PVM/variance/anomaly/drilldown;
- claim/evidence/verification;
- OpenTelemetry;
- ≥200-case evaluation;
- SQL Inspector / Evidence / Eval / Trace UI.

## P1 — strong differentiation

- proactive insight watcher;
- richer anomaly/reconciliation/sensitivity;
- stronger schema linking/RAG;
- OIDC/resource authorization;
- deployment hardening;
- performance/cost optimization;
- ≥500-case evaluation.

## P2 — platform depth

- asynchronous/distributed execution when justified;
- warehouse adapters;
- semantic governance lifecycle;
- advanced A/B and red-team evaluation;
- measured scale/load testing.

---

**This document is frozen as the v2 implementation contract. Any scope reduction that removes a P0 JD capability must be explicitly documented rather than silently redefining “complete”.**
