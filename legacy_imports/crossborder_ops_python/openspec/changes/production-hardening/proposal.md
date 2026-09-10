# Production Hardening

## Why
The Python backend currently works as a teaching demo but lacks production guardrails: health checks fail hard when MySQL is down, auth is demo-only, errors are inconsistent, and there is no request traceability.

## What Changes
- Add production settings with environment-driven auth, rate limiting, and CORS.
- Add stable health/readiness responses.
- Add request IDs, structured logs, and consistent error payloads.
- Add token signing/verification suitable for classroom and small production demos.
- Keep existing Vue-compatible endpoints unchanged.

## Non-Goals
- No RAG, MCP, multi-agent orchestration, platform API integration, or Kubernetes in this change.
