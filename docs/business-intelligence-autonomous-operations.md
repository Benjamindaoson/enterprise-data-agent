# Business Intelligence & Autonomous Operations Upgrade

## Product definition

The repository is being extended from a governed analytical agent into an
**Enterprise Business Intelligence & Autonomous Operations Agent**.

The design keeps the existing evidence-native analytical core and adds a
business-operations layer for four scenario families:

1. **Business analytics** — self-service data access, governed metrics,
   multi-dimensional analysis, attribution and evidence-backed findings.
2. **Marketing budget** — historical performance review, constrained budget
   allocation and scenario simulation, with human approval before any
   financial commitment.
3. **Sales expansion** — merchant/account eligibility, opportunity ranking and
   governed CRM handoff.
4. **Monetization** — opportunity discovery, product matching and revenue
   simulation with verification before recommendations are surfaced.

## Architecture

```text
Business Goal
    |
    v
Business Scenario Router
    |
    +-------------------+--------------------+-------------------+
    |                   |                    |                   |
 Analytics        Marketing Budget     Sales Expansion      Monetization
    |                   |                    |                   |
    +-------------------+--------------------+-------------------+
                            |
                            v
                       Skill Runtime
               representation / registry /
                 routing / composition
                            |
                            v
                     Agent Runtime / Harness
              task state / context / memory /
             budget / checkpoint / recovery
                            |
                            v
                        Tool Protocol
             SQL / Python / RAG / CRM /
              campaign / simulation tools
                            |
                            v
                 Evidence + Verification
                            |
                            v
                HITL / Policy / Audit Gate
                            |
                            v
                 External Action (optional)
```

## Runtime capability map

| Capability | Implementation |
| --- | --- |
| Agent loop / durable task state | Existing Supervisor/Executor and task-state contracts |
| Context engineering | Existing role/task context assembly and context versions |
| Long-term memory | Layered working, episodic, semantic and procedural memory contracts |
| Multi-agent | Existing controlled Supervisor/Executor model |
| Skill system | Typed SkillDefinition + SkillRegistry with permissions and tool dependencies |
| Tool protocol | Typed tool/action contracts, idempotency keys, permissions and bounded parameters |
| Checkpoint / resume | Existing checkpoint artifact and replay APIs |
| Failure recovery | Existing recovery-oriented runtime and trace records |
| Cost control | Tool-call and token runtime budgets |
| Observability | Existing OpenTelemetry + trace/event surfaces |
| Trajectory replay | Existing replay surface plus structured task events |
| HITL | Financial actions are blocked until explicit approval |
| Safety | Permission checks, financial-write policy, dry-run external actions |
| Evidence | Existing Claim -> Evidence -> Verification pipeline |

## Skill model

Every skill has:

- stable `skill_id` and version;
- description;
- input/output schema;
- tool dependencies;
- required permissions;
- searchable tags.

Current reference skills:

- `business.metric_analysis`
- `business.attribution`
- `business.marketing_budget`
- `business.sales_expansion`
- `business.monetization`
- `runtime.verify_action`

The registry is intentionally deterministic. Future skill evolution should
promote a candidate skill only after replayable offline evaluation rather than
allowing production trajectories to rewrite executable skills automatically.

## Memory model

The runtime separates four memory types:

- **Working memory**: active task facts and intermediate state.
- **Episodic memory**: prior trajectories and outcomes.
- **Semantic memory**: governed business definitions and stable domain facts.
- **Procedural memory**: reusable skills and verified procedures.

Memory entries are versioned and may expire. This prevents long-horizon context
management from degenerating into an unbounded chat transcript.

## Safety and autonomous actions

The public repository does **not** claim live access to proprietary campaign,
CRM or merchant systems.

External actions are therefore represented as typed proposals. Financial
commitments require:

1. policy permission;
2. human approval;
3. idempotency key;
4. budget checks;
5. auditable action metadata.

The public implementation reports `external_writes_executed = false`.

## Post-training boundary

The target architecture supports a later trajectory -> failure mining -> data
construction -> SFT/RL evaluation loop. The repository must not claim a trained
SFT/GRPO checkpoint until a real dataset, training run and reproducible
evaluation are committed.

Recommended training targets are narrowly scoped to:

- analytical planning;
- skill/tool selection;
- tool argument construction;
- recovery decisions;
- stop/continue decisions.

RL should only be added when a measurable failure mode remains after simpler
prompt, tool and harness improvements.

## API

### Capabilities

`GET /api/v1/capabilities`

Returns the supported business scenarios, runtime capabilities, skills and the
explicit limits of the public reference implementation.

### Business task planning

`POST /api/v1/business-tasks`

Example request:

```json
{
  "scenario": "MARKETING_BUDGET",
  "question": "Allocate the remaining budget across eligible segments.",
  "success_metrics": ["roi", "incremental_revenue"],
  "constraints": [
    {"name": "budget", "operator": "<=", "value": 1000000, "unit": "CNY"}
  ],
  "dry_run": true,
  "max_tool_calls": 20,
  "max_tokens": 24000
}
```

The response contains a typed execution plan, estimated runtime budget,
capabilities used and policy/HITL checks.

## JD coverage

### Agent Engineer (Business Intelligence)

Covered by the existing runtime plus this upgrade:

- Agent Loop
- context engineering and compression
- long-term memory contracts
- Multi-Agent / delegation
- tool protocol
- inference budget controls
- execution reliability
- safety and HITL
- Skill system
- persistent state and resume
- sandboxed execution
- observability / tracing
- replay
- evaluation and data-loop hooks

### BA Agent

Covered by the analytical core plus business scenario layer:

- self-service analytics
- NL2SQL / governed data tools
- Semantic Layer
- multi-dimensional drill-down
- attribution
- visualization/report artifacts
- RAG-compatible business knowledge
- Function Calling / tool use
- code execution sandbox
- multi-step planning
- evidence verification

### Agent Algorithm Engineer (Business Intelligence)

The repository now contains the runtime interfaces required for:

- Skill representation / organization / scheduling
- context and memory
- cost and execution optimization
- trajectory collection
- evaluation
- Prompt/SFT/RL extension points

**Not yet claimed as complete:** real SFT/GRPO training, measured AgentRL gains,
or live production marketing/CRM integrations. Those require separate,
reproducible implementation and experiments.
