# Governed PostgreSQL Enterprise Connector

The PostgreSQL connector is the first real enterprise data connector for the BA
Agent. It is intentionally narrow and production-shaped instead of advertising a
large list of unverified integrations.

## End-to-end contract

```text
connect
  -> introspect allowlisted catalog
  -> validate / infer semantic package
  -> compile typed metric + dimension request
  -> enforce schema/table/column permissions
  -> execute in a read-only transaction with statement timeout
  -> capture query + semantic provenance as evidence
  -> produce a decision-ready report
```

The connector never accepts arbitrary user SQL. Metric aggregations and
dimensions are represented as typed semantic definitions and resolved against
the live introspected catalog before a query can execute.

## Environment

- `EIW_ENTERPRISE_POSTGRES_URL` — SQLAlchemy PostgreSQL URL.
- `EIW_ENTERPRISE_POSTGRES_SCHEMAS` — required comma-separated schema allowlist.
- `EIW_ENTERPRISE_POSTGRES_TABLES` — optional fully-qualified table allowlist.
- `EIW_ENTERPRISE_POSTGRES_MAX_ROWS` — result cap, default 200.
- `EIW_ENTERPRISE_POSTGRES_TIMEOUT_MS` — statement timeout, default 5000.

API routes are under `/api/v1/connectors/postgres`.

## Proof

The production-integration GitHub Actions job launches PostgreSQL and exercises
the full flow against a real schema/table: connection, introspection, semantic
validation, permission checks, aggregate analysis, evidence hashing and report
construction.
