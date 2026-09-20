# ADR-004: Evidence Chain Architecture

**Status:** Accepted

**Date:** 2024

---

## Context

Enterprise Data Agent v2 produces analysis conclusions (Claims) that must be supported by verifiable Evidence. The evidence chain ensures:
- Every claim has backing evidence
- Evidence can be traced back to raw data
- Results are reproducible
- Audit requirements are met

---

## Evidence Chain Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLAIM                                     │
│  "Total Q1 sales were $5.2M"                                     │
└─────────────────────────────────────────────────────────────────┘
                              │ supported_by
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        EVIDENCE                                  │
│  - tool: sql_executor v1.0                                       │
│  - computation: sum(sales.amount) WHERE quarter=1                │
│  - result_hash: sha256(result)                                  │
│  - snapshot: snap-2024-q1                                        │
└─────────────────────────────────────────────────────────────────┘
                              │ based_on
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OBSERVATION                                │
│  "Sum of sales.amount = 5,234,567.89"                           │
│  - dimensions: {quarter: Q1, year: 2024}                        │
│  - numeric_values: {sum: 5234567.89, count: 125000}             │
└─────────────────────────────────────────────────────────────────┘
                              │ produced_by
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION RECORD                              │
│  - tool: sql_executor                                           │
│  - parameters: {query: "...", params: {quarter: 1}}             │
│  - started_at: 2024-04-01T10:00:00Z                             │
│  - completed_at: 2024-04-01T10:00:05Z                           │
│  - duration_ms: 5000                                            │
│  - result_row_count: 125000                                     │
└─────────────────────────────────────────────────────────────────┘
                              │ reads_from
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATASET SNAPSHOT                               │
│  - snapshot_id: snap-2024-q1                                    │
│  - tables: [sales, products, stores]                            │
│  - schema_hash: sha256(schema)                                  │
│  - row_counts: {sales: 500000, products: 10000, stores: 500}    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Evidence Validation Rules

1. **Completeness**: Every Claim must have at least one Evidence
2. **Hash Integrity**: Evidence.result_hash must match recomputed value
3. **Snapshot Pinning**: Evidence must reference a pinned DatasetSnapshot
4. **Tool Versioning**: Evidence must record tool name and version
5. **Reproducibility**: Same inputs must produce same outputs

---

## Claim-Evidence Relationships

| Relationship | Description |
|--------------|-------------|
| `SUPPORTS` | Evidence directly supports the claim |
| `REFUTES` | Evidence contradicts the claim |
| `NEUTRAL` | Evidence is unrelated to the claim |
| `PARTIAL` | Evidence partially supports the claim |

---

## Implementation

```python
@dataclass
class EvidenceChain:
    claim: Claim
    evidence: list[Evidence]
    observations: list[Observation]
    execution_records: list[ExecutionRecord]
    dataset_snapshot: DatasetSnapshot

    def validate(self) -> ValidationResult:
        """Validate evidence chain integrity."""
        # Check all claims have evidence
        # Verify result hashes
        # Confirm snapshot references
        # Validate temporal consistency
```

---

## Consequences

### Positive
- Full traceability from conclusions to raw data
- Reproducible results via snapshot pinning
- Clear audit trail for governance

### Negative
- Additional storage for evidence chain
- Performance overhead for hash computation
- Complexity in evidence management
