# MVP Build Blocker Report

## Exact blocker

The Cloud execution environment cannot establish an outbound HTTPS tunnel to `data.iowa.gov`. The frozen MVP requires a real, immutable Iowa Liquor Sales/Stores/Products snapshot and measured metadata produced by an actual extraction. Continuing with fabricated metadata or a synthetic flagship dataset would violate the frozen data contract.

## Phase

Phase 0A — Data Foundation, official source discovery and extraction.

## Command/action

The following non-destructive Python connectivity probe was run from the repository:

```bash
python - <<'PY'
import urllib.request
for u in [
    'https://data.iowa.gov/api/views/m3tr-qhgy',
    'https://data.iowa.gov/api/catalog/v1?search_context=data.iowa.gov&q=Iowa%20Liquor%20Sales',
]:
    try:
        data = urllib.request.urlopen(u, timeout=20).read(500)
        print(u, data[:200])
    except Exception as exc:
        print(type(exc).__name__, exc)
PY
```

## Error

Both independent official routes failed before reaching the source:

```text
URLError <urlopen error Tunnel connection failed: 403 Forbidden>
URLError <urlopen error Tunnel connection failed: 403 Forbidden>
```

An internet search fallback also failed with `401 Unauthorized`, so it could not be used to discover an alternate official download route.

## Recovery attempts

1. Probed the known Socrata asset metadata endpoint.
2. Probed the official Socrata catalog discovery endpoint rather than relying on a remembered asset identifier.
3. Attempted internet search for the current official table/API location.
4. Confirmed that the failure is at the environment tunnel/proxy layer, not an Iowa API response, schema error, query limit, or application bug.

## Why autonomous recovery failed

Every available network path was rejected by the environment before a response from the official publisher was received. The repository contains architecture documents only and no previously measured snapshot, manifest, release artifact, or approved offline mirror. The frozen design expressly forbids:

- inventing row counts, timestamps, checksums, fingerprints, or profiles;
- replacing the official flagship snapshot with controlled synthetic fixtures;
- advancing a snapshot to `READY` without invoice uniqueness, date coverage, reconciliation, reference coverage, and checksum validation;
- proceeding to benchmark and later MVP phases without the Phase 0A gate.

Consequently, meaningful implementation beyond an unvalidated skeleton would create a misleading claim of progress and could not satisfy the MVP Definition of Done.

## Minimum human action required

Perform **one** of the following:

1. Enable outbound HTTPS access from this environment to `data.iowa.gov` (including its API/download hosts); or
2. Place the three unmodified official source exports in an accessible local directory outside normal Git history and provide their exact paths:
   - Iowa Liquor Sales for `2024-01-01 <= ordered_on < 2026-08-01`;
   - Iowa Liquor Stores current reference snapshot;
   - Iowa Liquor Products current reference snapshot.

The files must be traceable to the official publisher. Credentials are not required for the public data, and no secret should be committed.

## Exact resume instructions

1. Resume on branch `mvp-build` in `/workspace/enterprise-data-agent`.
2. Verify access with:

   ```bash
   python -c "import urllib.request; print(urllib.request.urlopen('https://data.iowa.gov', timeout=20).status)"
   ```

   If offline exports were supplied, instead record their paths and run SHA-256 checks before transformation.
3. Re-run official asset discovery and record the actual asset identifiers, licenses, source update timestamps, extraction queries, and extraction timestamp.
4. Extract immutable Raw Parquet for the frozen interval, then measure invoice uniqueness, duplicates, nulls, signed adjustments, cost availability, and reference coverage.
5. Build Curated Parquet and DuckDB views; run Raw/Curated and LEFT JOIN reconciliation for row count, sales dollars, and bottles.
6. Generate the measured manifest and deterministic ground truth. Only then change Phase 0A from `BLOCKED` to `PASSED` and continue automatically through Phase 4.
