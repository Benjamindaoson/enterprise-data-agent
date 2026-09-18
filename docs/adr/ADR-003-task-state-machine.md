# ADR-003: Analysis Task State Machine

**Status:** Accepted

**Date:** 2024

---

## Context

The Analysis Task is the central entity in Enterprise Data Agent v2. It tracks the lifecycle of an analysis request from creation through completion. The state machine ensures:
- Predictable workflow progression
- Proper error handling and recovery
- Audit trail for compliance

---

## State Definitions

| State | Description |
|-------|-------------|
| `CREATED` | Task received, initial validation complete |
| `PLANNING` | Supervisor creating analysis plan |
| `CLARIFICATION_NEEDED` | User input required to proceed |
| `EXECUTING` | Plan being executed by executor |
| `COMPLETED` | Analysis finished successfully |
| `FAILED` | Unrecoverable error occurred |
| `CANCELLED` | User cancelled the task |

---

## Transition Rules

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│ CREATED │───▶│ PLANNING │───▶│ EXECUTING │───▶│COMPLETED │ │
└─────────┘    └──────────┘    └──────────┘    └──────────┘ │
     │              │                 │                       │
     │              │                 │                       │
     │              ▼                 ▼                       │
     │    ┌──────────────────┐  ┌─────────┐                   │
     │    │ CLARIFICATION   │  │ FAILED  │◀──────────────────┘
     │    │ _NEEDED         │  └─────────┘    (can retry)
     │    └──────────────────┘        ▲
     │              │                │
     ▼              ▼                │
  ┌─────────┐      │                │
  │CANCELLED│◀─────┴────────────────┘
  └─────────┘
```

### Detailed Transitions

| From | To | Trigger |
|------|-----|---------|
| CREATED | PLANNING | Supervisor begins planning |
| CREATED | FAILED | Invalid task configuration |
| CREATED | CANCELLED | User cancels |
| PLANNING | EXECUTING | Plan ready, user approved |
| PLANNING | CLARIFICATION_NEEDED | Missing user input |
| PLANNING | FAILED | Planning error |
| PLANNING | CANCELLED | User cancels |
| CLARIFICATION_NEEDED | PLANNING | User provides input |
| CLARIFICATION_NEEDED | CANCELLED | User cancels |
| EXECUTING | COMPLETED | All steps successful |
| EXECUTING | FAILED | Execution error |
| EXECUTING | CANCELLED | User cancels |
| FAILED | PLANNING | Retry initiated |
| CANCELLED | - | Terminal state |

---

## State Metadata

Each state transition records:
- `timestamp`: When transition occurred
- `actor`: Who/what triggered transition
- `reason`: Why transition occurred
- `checkpoint`: State snapshot for recovery

---

## Implementation

```python
class TaskStateMachine:
    VALID_TRANSITIONS = {
        TaskState.CREATED: [TaskState.PLANNING, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.PLANNING: [TaskState.EXECUTING, TaskState.CLARIFICATION_NEEDED, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.CLARIFICATION_NEEDED: [TaskState.PLANNING, TaskState.CANCELLED],
        TaskState.EXECUTING: [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.COMPLETED: [],
        TaskState.FAILED: [TaskState.PLANNING],
        TaskState.CANCELLED: [],
    }

    def transition(self, from_state: TaskState, to_state: TaskState) -> bool:
        if to_state in self.VALID_TRANSITIONS.get(from_state, []):
            # Execute transition
            return True
        return False
```

---

## Consequences

### Positive
- Clear workflow states prevent invalid operations
- Recovery paths enable retry after failures
- Audit trail captures all state changes

### Negative
- Complex state logic requires careful implementation
- Multiple paths can make debugging harder
