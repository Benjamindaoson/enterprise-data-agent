# ADR-001: Enterprise Data Agent v2 Architecture

**Status:** Accepted

**Date:** 2024

**Deciders:** Enterprise Data Agent Team

---

## Context

Enterprise Data Agent v2 is a domain-driven, policy-enforced data analysis system that provides:
- Semantic understanding of business metrics and dimensions
- Evidence-based claim validation
- Audit-compliant analysis workflows
- Reproducible results through dataset snapshots

This ADR documents the foundational architectural decisions for Phase 0A (Contracts & Benchmark).

---

## Decision Drivers

1. **Separation of Concerns**: Domain logic must be independent of persistence and API frameworks
2. **Semantic Parity**: Analysis must preserve deterministic semantics across executions
3. **Auditability**: All decisions and data accesses must be traceable
4. **Policy Enforcement**: Governance rules must be enforced at runtime
5. **Evaluation-Ready**: System must support automated testing via golden cases

---

## Decisions

### 1. Domain Model Architecture

**Decision:** Use Pydantic v2 for domain models with strict type validation.

**Rationale:**
- Pydantic provides automatic validation, serialization, and JSON Schema generation
- Models are framework-agnostic and can be used in any context
- Type hints enable static analysis with mypy

**Implementation:**
```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class AnalysisTask(BaseModel):
    task_id: UUID
    business_question: str = Field(..., min_length=1)
    state: TaskState
    created_at: datetime
```

**Consequences:**
- All domain objects are immutable by default (frozen=True option)
- Validation errors raise clear, actionable messages
- JSON serialization is deterministic

### 2. State Machine for Analysis Tasks

**Decision:** Implement explicit state machine with defined transitions.

**States:**
- `CREATED` → Initial state when task is submitted
- `PLANNING` → Supervisor is creating analysis plan
- `CLARIFICATION_NEEDED` → More information required from user
- `EXECUTING` → Analysis plan is being executed
- `COMPLETED` → Analysis finished successfully
- `FAILED` → Analysis encountered an unrecoverable error
- `CANCELLED` → Analysis cancelled by user

**Transitions:**
```
CREATED → [PLANNING, FAILED, CANCELLED]
PLANNING → [EXECUTING, CLARIFICATION_NEEDED, FAILED, CANCELLED]
CLARIFICATION_NEEDED → [PLANNING, CANCELLED]
EXECUTING → [COMPLETED, FAILED, CANCELLED]
COMPLETED → [] (terminal)
FAILED → [PLANNING] (can retry)
CANCELLED → [] (terminal)
```

### 3. Semantic Package Structure

**Decision:** Use versioned YAML files for semantic definitions.

**Structure:**
```yaml
version: "1.0.0"
domain_id: "iowa_liquor_wholesale"

metrics:
  - metric_id: total_sales
    name: Total Sales
    description: Sum of all sales
    aggregation: sum
    unit: "$"

dimensions:
  - dimension_id: region
    name: Region
    values: [North, South, East, West]

join_policies:
  - left: sales
    right: products
    on: product_id
    type: many_to_one
```

**Rationale:**
- Human-readable and version-controllable
- Can be loaded at startup or runtime
- Enables semantic validation of analysis requests

### 4. Evaluation Framework

**Decision:** Use golden case evaluation with deterministic fixtures.

**Components:**
- **EvaluationCase**: Defines input, expected output, and acceptance criteria
- **EvaluationRun**: Records execution metadata (version, timestamp)
- **EvaluationResult**: Captures pass/fail and failure categories

**Failure Categories:**
- `INCORRECT_METRIC`: Wrong metric computed
- `WRONG_TIME_PERIOD`: Incorrect time filter
- `INCORRECT_FILTER`: Wrong dimension filter
- `INVALID_AGGREGATION`: Wrong aggregation function
- `MISSING_EVIDENCE`: Required evidence not produced
- `CONTRADICTORY_CLAIMS`: Conflicting claims produced
- `INSUFFICIENT_COVERAGE`: Not all required metrics/dimensions covered
- `POLICY_VIOLATION`: Governance policy violated

### 5. Evidence Chain Architecture

**Decision:** Every claim must be backed by evidence with full lineage.

**Structure:**
```
Claim ← Evidence ← Observation ← ExecutionRecord
                    ↓
              DatasetSnapshot
```

**Validation:**
- Evidence hash must match recomputed result
- Dataset snapshot must be pinned
- Execution must be reproducible

### 6. Persistence Strategy

**Decision:** Use SQLAlchemy 2.0 with PostgreSQL for persistence.

**Tables:**
- `analysis_task`: Core task state
- `analysis_context`: Resolved intent and data availability
- `analysis_plan`: Execution plan with steps
- `hypothesis`: Research hypotheses
- `execution_record`: Tool execution history
- `observation`: Computed observations
- `claim`: Business conclusions
- `evidence`: Supporting evidence with lineage
- `validation_result`: Validation outcomes
- `artifact`: Generated artifacts (reports, charts)
- `domain_event`: Event log for tracing
- `audit_event`: Audit trail for governance

### 7. Tracing and Observability

**Decision:** Implement OpenTelemetry-style distributed tracing.

**Spans:**
- Task lifecycle spans
- Tool execution spans
- Validation spans
- Hypothesis evaluation spans

**Attributes:**
- `task.id`, `task.state`
- `execution.tool_name`, `execution.duration_ms`
- `hypothesis.state`, `claim.type`

### 8. Governance Model

**Decision:** Implement RBAC with seven enterprise roles.

**Roles:**
- `ADMIN`: Full system access
- `ANALYST`: Can create and run analyses
- `VIEWER`: Read-only access
- `DATA_STEWARD`: Manages semantic packages
- `AUDITOR`: Access to audit logs
- `EVALUATOR`: Runs evaluation suites
- `SYSTEM`: Internal operations

---

## Consequences

### Positive
- Clear separation enables independent testing of each layer
- Policy enforcement ensures governance compliance
- Evaluation framework enables continuous quality assurance
- Semantic package enables domain expert validation

### Negative
- Additional complexity in model definitions
- Need for migration management
- Version coordination between components

### Risks
- Semantic package changes may require model updates
- State machine complexity may lead to edge cases
- Snapshot management overhead

---

## References

- [Enterprise Data Agent v2 JD Parity Spec](../docs/ENTERPRISE_DATA_AGENT_V2_JD_PARITY_SPEC.md)
- [Phase 0 Implementation Plan](./phase-0-implementation-plan.md)
- [Semantic Package Schema](./semantic-package-schema.md)
