# ADR-002: Semantic Package Versioning Strategy

**Status:** Accepted

**Date:** 2024

---

## Context

The Enterprise Data Agent relies on semantic packages to define business metrics, dimensions, and their relationships. As business requirements evolve, these semantic definitions must be updated while maintaining backward compatibility and reproducibility.

---

## Decision

Use semantic versioning (MAJOR.MINOR.PATCH) with the following rules:

### Version Bumping Rules

**PATCH (x.y.Z):** Backward-compatible bug fixes
- Fixing incorrect metric descriptions
- Adding new dimension values within existing dimensions
- Improving documentation

**MINOR (x.Y.0):** Backward-compatible feature additions
- Adding new metrics
- Adding new dimensions
- Adding new join policies
- Adding new allowed filters

**MAJOR (X.0.0):** Breaking changes
- Renaming metrics or dimensions
- Changing aggregation functions
- Changing metric definitions
- Removing existing metrics or dimensions
- Changing join policy semantics

### Snapshot Pinning

Analysis tasks must pin to a specific semantic package version at creation time:
```python
task = AnalysisTask(
    policy_version="1.0.0",
    semantic_package_version="2.1.0",
    dataset_snapshot_identifier="snap-2024-q1",
)
```

This ensures:
1. Reproducibility: Same inputs produce same outputs
2. Auditability: Historical analysis can be traced to exact definitions
3. Upgrade control: Teams can upgrade on their schedule

---

## Consequences

### Positive
- Clear upgrade path for semantic package changes
- Historical analyses remain reproducible
- Teams control their upgrade timing

### Negative
- Multiple versions must be maintained in production
- Compatibility testing across versions

---

## Implementation Notes

- Semantic packages are stored in `semantic_packages/{domain_id}/semantic-package.yaml`
- Version is specified in the YAML header
- Package loader validates version format on load
- Analysis tasks record version in task metadata
