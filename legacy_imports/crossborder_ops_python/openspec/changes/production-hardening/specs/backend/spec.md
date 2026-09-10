## ADDED Requirements

### Requirement: Stable Operational Health
The backend SHALL expose liveness and readiness endpoints that return structured JSON even when external dependencies fail.

#### Scenario: Database unavailable
- **WHEN** the database connection raises an exception
- **THEN** readiness returns a JSON status of `DOWN`
- **AND** the API does not return an unhandled stack trace

### Requirement: Authenticated API Mode
The backend SHALL support a demo mode and an authenticated mode without changing frontend endpoint paths.

#### Scenario: Auth enabled request without token
- **GIVEN** auth is enabled
- **WHEN** a protected endpoint is called without a valid token
- **THEN** the API returns HTTP 401 with a structured error payload

### Requirement: Request Traceability
Every HTTP response SHALL include a request id and errors SHALL include the same request id.

#### Scenario: Validation error
- **WHEN** a request body is invalid
- **THEN** the response contains `requestId`, `code`, and `message`

### Requirement: Agent Observability
The backend SHALL emit structured events for Tool and LLM execution and expose aggregate counters.

#### Scenario: Tool execution
- **WHEN** the Agent routes a user question to a Tool
- **THEN** a structured Tool event is logged
- **AND** `/metrics` exposes an Agent event counter

### Requirement: Distributed Rate Limiting
The backend SHALL support Redis-backed rate limiting for multi-worker deployments and fall back to memory for local demos.

#### Scenario: Redis configured
- **WHEN** `REDIS_URL` is configured and reachable
- **THEN** request limits are counted through Redis

### Requirement: Database Migrations
The backend SHALL define Alembic migrations for the current business schema.

#### Scenario: Fresh database
- **WHEN** `alembic upgrade head` is executed
- **THEN** the cross-border store, SKU, order, refund, ad, review, and listing tables are created

### Requirement: Production Identity Provider
The backend SHALL support a real OIDC/JWKS authentication mode without removing the classroom login-code mode.

#### Scenario: OIDC mode
- **WHEN** `IDENTITY_PROVIDER=oidc` is configured with issuer, audience, and JWKS URL
- **THEN** protected API requests are validated through the external identity provider's public keys

### Requirement: Agent Regression Evaluation
The backend SHALL include deterministic eval cases for the core Agent-to-Tool behavior.

#### Scenario: Eval runner
- **WHEN** `python -m app.eval_runner` runs
- **THEN** business summary, chart, refund, ad, and review routing cases are checked
