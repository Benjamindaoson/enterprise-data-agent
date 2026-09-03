# Full Product Completion Specification

> Status: Product acceptance baseline v0.1  
> Date: 2026-09-02  
> Purpose: Define whether the Iowa single-domain Enterprise Intelligence Workspace is a complete usable product.

## 0. Acceptance principle

This document is the product acceptance checklist. It is not a replacement for
the architecture documents and it does not require every internal capability to
be a separate service.

A feature is `COMPLETE` only when every applicable dimension is `PASS`:

```text
Feature Complete = UI × Backend × AI × Data × Integration × Security ×
                   Exception × Test × Demo
```

If a dimension is not applicable, it is marked `N/A`. A route, class, migration,
placeholder, or static screen alone is not evidence of completion.

## 1. Status vocabulary

| Status | Meaning |
| --- | --- |
| `PASS` | Implemented, integrated, tested, and demonstrable in the declared scope |
| `PARTIAL` | Some behavior exists, but at least one required path or guarantee is missing |
| `FAIL` | The behavior exists but violates a product or trust requirement |
| `N/A` | The dimension does not apply to this capability |
| `NOT COMPLETE` | The feature-level multiplication rule is not satisfied |

Current status is evaluated against the local reference product and the intended
single-domain MVP. `local-reference` means the current deterministic JSON/file
implementation can demonstrate a narrow happy path; it is not a release status.

## 2. Product-area master list

| Area | Required user outcome | Current status | Main gap |
| --- | --- | --- | --- |
| Today / Home | See data state, KPI pulse, recent work, suggestions, and start actions | `PARTIAL` | Local page exists; no authenticated user scope and limited KPI/workspace pulse |
| New Analysis | Enter a question, resolve scope, and receive clarification when needed | `PARTIAL` | Regex-based deterministic resolution; no real AI ambiguity handling or async task start |
| Analysis Workspace | Follow task state, context, plan, findings, and current conclusion | `PARTIAL` | Static single-process workflow; no real live task lifecycle |
| Investigation | See hypotheses, steps, drill-down, and support/refute/unknown states | `PARTIAL` | Hypotheses are hard-coded; no autonomous conditional investigation loop |
| Dynamic BI | Explore KPI, trend, comparison, contribution, PVM, and drill-down | `PARTIAL` | Basic views exist; missing real filters, cross-navigation, mix-shift and chart model |
| Evidence | Traverse Claim → Evidence → Computation → Data → Version → Validation | `PARTIAL` | Links exist but execution/provenance/validation are incomplete |
| Report | Read/export executive summary, findings, drivers, evidence, limits, recommendations | `PARTIAL` | Markdown/HTML exists; report is composed before claims and lacks full faithfulness checks |
| Follow-up | Continue an analysis as an authorized child task with reusable context/evidence | `PARTIAL` | Parent link exists; compatibility and evidence authorization are not revalidated |
| History | Reopen, inspect lineage, and replay prior work | `PARTIAL` | History works; replay is only a marker and does not resume execution |
| Data Status | Inspect source, version, freshness, row count, quality, and restrictions | `PARTIAL` | Manifest/status exists; independent Store/Product source snapshots are absent |
| Semantic Explorer | Inspect metrics, formulas, dimensions, rules, validity, and source | `PARTIAL` | YAML is visible; runtime metric surface is not fully aligned with the package |
| Evaluation | Run Golden Cases, inspect metrics, failures, and regressions | `PARTIAL` | Current scorer omits major expectations and auto-passes controlled fixtures |
| Settings | Inspect provider, versions, budgets, limits, and credentials | `PARTIAL` | Read-only settings page exists; settings are not fully wired to runtime behavior |
| System States | Correctly render loading, clarification, partial, abstain, failed, cancelled, unavailable | `PARTIAL` | Several states are returned; frontend and resume/error flows are incomplete |

## 3. Capability matrix: 59 architecture capabilities

Legend for the dimension columns: `P` = pass, `△` = partial, `F` = fail,
`—` = not applicable. The last column is the authoritative feature status.

### 3.1 Experience & Collaboration Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXP-01 | Analysis Workspace | △ | P | △ | P | △ | F | △ | △ | P | NOT COMPLETE |
| EXP-02 | Investigation View | △ | △ | F | △ | △ | F | △ | F | P | NOT COMPLETE |
| EXP-03 | Evidence View | △ | △ | — | △ | △ | F | △ | F | P | NOT COMPLETE |
| EXP-04 | Chart / Dashboard View | △ | △ | — | △ | F | F | △ | F | P | NOT COMPLETE |
| EXP-05 | Report Workspace | △ | P | — | △ | △ | F | △ | F | P | NOT COMPLETE |

Evidence: [web UI](../src/eiw/web/static/index.html), [API](../src/eiw/app.py),
[analysis workflow](../src/eiw/workspace/analysis.py).

### 3.2 Analytical Intelligence Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ANA-01 | Business Understanding | P | △ | F | △ | △ | F | △ | △ | P | NOT COMPLETE |
| ANA-02 | Semantic Resolution Request | P | △ | F | P | △ | F | △ | △ | P | NOT COMPLETE |
| ANA-03 | Analysis Planning | P | △ | F | △ | △ | F | △ | △ | P | NOT COMPLETE |
| ANA-04 | Hypothesis Management | P | △ | F | △ | △ | F | F | F | P | NOT COMPLETE |
| ANA-05 | Investigation Policy | — | F | F | — | F | F | F | F | F | NOT COMPLETE |
| ANA-06 | Conclusion and Recommendation Synthesis | P | △ | F | △ | △ | F | △ | F | P | NOT COMPLETE |

The current planner is a fixed three-step plan and the provider is a no-op
deterministic placeholder; see [provider](../src/eiw/workspace/provider.py:15)
and [workflow](../src/eiw/workspace/analysis.py:222).

### 3.3 Enterprise Context Intelligence Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CTX-01 | Semantic & Metric System | P | △ | — | P | △ | F | △ | △ | P | NOT COMPLETE |
| CTX-02 | Domain Business Rules | P | △ | — | △ | △ | F | △ | △ | P | NOT COMPLETE |
| CTX-03 | Schema and Catalog Metadata | P | F | — | △ | F | F | F | F | △ | NOT COMPLETE |
| CTX-04 | Metric Dependency and Join Relationships | P | F | — | △ | F | F | F | △ | △ | NOT COMPLETE |
| CTX-05 | Data Quality and Freshness | P | △ | — | △ | △ | F | △ | △ | P | NOT COMPLETE |
| CTX-06 | User / Role / Policy Context | — | F | — | — | F | F | F | F | F | NOT COMPLETE |
| CTX-07 | Context Compiler | △ | △ | F | △ | F | F | △ | △ | P | NOT COMPLETE |

The YAML package is real, but the runtime context is a simplified dictionary,
not the required staged immutable Context Package. See [semantic package](../semantic_packages/iowa_liquor_wholesale/semantic-package.yaml)
and [context construction](../src/eiw/workspace/analysis.py:157).

### 3.4 Agent Runtime Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RUN-01 | Task Lifecycle | △ | △ | — | △ | △ | F | △ | △ | P | NOT COMPLETE |
| RUN-02 | State Persistence | P | △ | — | △ | F | F | △ | △ | P | NOT COMPLETE |
| RUN-03 | Step Scheduling | △ | F | — | — | F | F | F | F | F | NOT COMPLETE |
| RUN-04 | Tool Routing | — | F | △ | △ | F | F | F | F | F | NOT COMPLETE |
| RUN-05 | Budget and Stop Conditions | △ | F | — | — | F | F | F | F | F | NOT COMPLETE |
| RUN-06 | Checkpoint / Resume | △ | F | — | △ | F | F | F | F | △ | NOT COMPLETE |
| RUN-07 | Retry / Failure Handling | △ | F | — | — | F | F | F | F | F | NOT COMPLETE |
| RUN-08 | Trace / Replay | △ | F | — | △ | F | F | F | F | △ | NOT COMPLETE |

The app uses a synchronous `AnalysisService` and a JSON store; its replay route
only records a replay marker. See [store](../src/eiw/workspace/store.py) and
[replay route](../src/eiw/app.py:129).

### 3.5 Governed Analysis Execution Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXE-01 | Read-only SQL Executor | — | △ | — | P | △ | △ | △ | △ | P | NOT COMPLETE |
| EXE-02 | SQL Validation and Policy Checks | — | △ | — | △ | F | F | F | F | △ | NOT COMPLETE |
| EXE-03 | Deterministic Statistical Tools | △ | △ | — | P | △ | F | △ | F | P | NOT COMPLETE |
| EXE-04 | Limited Dataframe Analysis | — | F | — | — | F | F | F | F | F | NOT COMPLETE |
| EXE-05 | Visualization Specification Renderer | △ | F | — | △ | F | F | △ | F | △ | NOT COMPLETE |
| EXE-06 | Execution Resource Limits | △ | F | — | △ | F | F | F | F | F | NOT COMPLETE |

Current SQL is assembled inside the data adapter and lacks the complete parse,
policy, resource, repair, and execution-record pipeline required by the design.

### 3.6 Evidence & Artifact Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVD-01 | Observation | P | △ | — | △ | △ | F | △ | F | P | NOT COMPLETE |
| EVD-02 | Claim | P | △ | F | △ | △ | F | △ | F | P | NOT COMPLETE |
| EVD-03 | Evidence | P | △ | — | △ | △ | F | △ | F | P | NOT COMPLETE |
| EVD-04 | Query / Computation Provenance | △ | F | — | △ | F | F | F | F | △ | NOT COMPLETE |
| EVD-05 | Validation Result | △ | F | — | △ | F | F | F | F | △ | NOT COMPLETE |
| EVD-06 | Chart Specification | F | F | — | △ | F | F | F | F | F | NOT COMPLETE |
| EVD-07 | Report Artifact | P | △ | — | △ | △ | F | △ | F | P | NOT COMPLETE |
| EVD-08 | Historical Analysis Artifact | △ | △ | — | △ | F | F | △ | F | △ | NOT COMPLETE |

The current chain stores dictionaries and validation labels rather than complete
independent execution, observation, validation, and provenance records. Report
composition also occurs before claims are created; see [artifact ordering](../src/eiw/workspace/analysis.py:207).

### 3.7 Enterprise Data Connectivity Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CON-01 | Database / Warehouse Connection Adapter | — | F | — | P | F | F | F | F | △ | NOT COMPLETE |
| CON-02 | Schema Introspection | △ | F | — | △ | F | F | F | F | △ | NOT COMPLETE |
| CON-03 | Query Pushdown | — | △ | — | P | F | F | F | F | △ | NOT COMPLETE |
| CON-04 | Source Identity and Permission Propagation | — | F | — | △ | F | F | F | F | F | NOT COMPLETE |
| CON-05 | Data Freshness Metadata | P | △ | — | △ | △ | F | △ | △ | P | NOT COMPLETE |

Only a local DuckDB reader exists. There is no connector port used by the
application and no enterprise source identity propagation.

### 3.8 Trust, Security & Governance Control Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TRU-01 | Identity and Tenant Context | △ | F | — | — | F | F | F | F | F | NOT COMPLETE |
| TRU-02 | RBAC / ABAC Policy | — | F | — | — | F | F | F | F | F | NOT COMPLETE |
| TRU-03 | Row / Column / Metric Access Policy | — | △ | — | △ | F | F | F | F | △ | NOT COMPLETE |
| TRU-04 | Query Policy and Resource Budget | — | △ | — | △ | F | F | F | F | △ | NOT COMPLETE |
| TRU-05 | Sensitive Data Handling | — | △ | — | △ | F | F | △ | F | △ | NOT COMPLETE |
| TRU-06 | Audit Events | — | F | — | — | F | F | F | F | F | NOT COMPLETE |
| TRU-07 | Artifact Classification and Sharing Policy | △ | F | — | △ | F | F | F | F | △ | NOT COMPLETE |

The public API accepts client-supplied `user_context`, and task/resource reads do
not enforce tenant or object authorization. See [task creation](../src/eiw/app.py:55).

### 3.9 Evaluation & Observability Control Plane

| ID | Capability | UI | Backend | AI | Data | Integration | Security | Exception | Test | Demo | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVA-01 | Golden Evaluation Cases | P | △ | — | △ | △ | F | △ | △ | P | NOT COMPLETE |
| EVA-02 | Domain Metrics | P | △ | — | △ | △ | F | F | F | △ | NOT COMPLETE |
| EVA-03 | Runtime Trace | P | F | — | △ | F | F | F | F | △ | NOT COMPLETE |
| EVA-04 | Failure Taxonomy | — | △ | — | — | F | F | △ | △ | △ | NOT COMPLETE |
| EVA-05 | Regression Comparison | △ | F | — | △ | F | F | F | F | F | NOT COMPLETE |
| EVA-06 | Human Review | F | F | — | — | F | F | F | F | F | NOT COMPLETE |
| EVA-07 | Cost / Latency Monitoring | F | F | — | — | F | F | F | F | F | NOT COMPLETE |

The current scorer checks only a subset of metrics and auto-passes controlled
fixtures. See [evaluation route](../src/eiw/app.py:193).

## 4. Cross-cutting user actions

| Action | Required behavior | Current status | Blocking issue |
| --- | --- | --- | --- |
| Create analysis | Create task, bind trusted identity, compile context, enqueue work, show progress | `PARTIAL` | Synchronous flow and client-supplied identity |
| Clarify | Persist answer and resume the original task | `NOT COMPLETE` | Endpoint changes state to PARTIAL; it does not resume |
| Cancel | Stop queued/running work safely | `PARTIAL` | State flag only; no worker cancellation |
| Follow up | Create child with authorized compatible context/evidence | `PARTIAL` | No compatibility or evidence authorization check |
| Inspect Evidence | Open complete provenance and validation chain | `NOT COMPLETE` | Missing real execution and validation entities in runtime |
| Replay | Re-run from checkpoint without duplicates | `NOT COMPLETE` | Replay only marks the task as replayable |
| Export report | Export a faithful report containing saved Claims/Evidence | `PARTIAL` | Artifact is created before Claims/Evidence |
| Run evaluation | Measure all declared expectations and categorize failures | `NOT COMPLETE` | Scorer omits numeric, grain, filters, claims, hypotheses and provenance checks |

## 5. Completion gates

The product cannot be called complete until all of the following are true:

1. Every row above is `COMPLETE`, or the capability is formally removed from the
   product specification through an accepted product decision.
2. All fourteen product areas have at least one end-to-end Playwright flow.
3. Every user action has success, loading, empty, error, partial, clarification,
   cancellation, and unavailable-state coverage where applicable.
4. The complete main path runs through real frontend → API → worker/runtime →
   PostgreSQL → DuckDB/Parquet → provider → Evidence → report.
5. The model may interpret and plan, but code owns formulas, permissions,
   versions, execution, validation, state, and evidence binding.
6. The evaluation suite checks semantic, time/filter/grain, numeric, plan,
   evidence, verification, policy, runtime, and report behavior.
7. A 1000-user / 20–30 concurrent-analysis target is load-tested on the declared
   single-machine deployment profile.

## 6. Immediate interpretation for the current repository

The repository currently satisfies a useful `local-reference` subset:

- real Iowa sales data is present and independently validated;
- the narrow deterministic analysis happy path runs;
- a basic UI, API, report, and local history exist;
- domain and semantic contracts provide a foundation.

It does not yet satisfy this Product Feature Master. The next engineering goal
should therefore be to move rows from `NOT COMPLETE` to `PASS`, starting with
trusted identity/security, the real task/runtime path, evidence correctness,
and a truthful evaluator. It should not be treated as a request to blindly
recreate every architecture diagram or to add distributed infrastructure before
those product gaps are closed.
