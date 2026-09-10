# Observability

## Logs

The API emits JSON logs for:

- HTTP requests;
- Tool start/success/error;
- LLM call start/success/error;
- LLM skipped when disabled or missing key.

Each HTTP response includes `x-request-id`.

## Metrics

`GET /metrics` returns Prometheus-style counters:

```text
crossborder_http_requests_total
crossborder_agent_events_total
```

## Traces

Set:

```text
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

The backend instruments:

- FastAPI requests;
- HTTPX calls to the LLM provider;
- SQLAlchemy database calls when an engine is supplied to instrumentation.

For local classroom runs, tracing is disabled by default.
