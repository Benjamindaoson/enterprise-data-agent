## Context

The isolated project currently contains a copied Java backend and Vue frontend from a sales analysis agent. It has a useful teaching architecture: chat UI, SSE streaming, LangChain4j agent, tool calls, service/repository metrics, database seed data, persistent chat memory, and ECharts rendering.

The project must become an independent course capstone. We will keep the architectural pattern but replace the domain and implementation details with a cross-border e-commerce operations scenario.

## Goals / Non-Goals

**Goals:**

- Build a runnable course MVP for a cross-border e-commerce operations agent.
- Keep the system understandable for Java backend students.
- Demonstrate the full enterprise AI loop: chat, tool calling, deterministic business services, database metrics, streaming UI, charts, and evaluation-ready demo questions.
- Replace the original sales domain with original cross-border commerce entities, tools, prompts, seed data, and frontend copy.
- Keep existing chat endpoints where practical to reduce integration churn.

**Non-Goals:**

- Do not modify any other copied course demo outside `crossborder-ops-agent`.
- Do not build a complete ERP or marketplace integration.
- Do not call real Amazon, TikTok Shop, logistics, or ad platform APIs in the MVP.
- Do not make MCP, A2A, RAG, or multi-agent orchestration first-version requirements.
- Do not make local Ollama or private model deployment a required runtime path for the first version.

## Decisions

### Decision: Keep a modular monolith

The MVP will remain one Spring Boot backend plus one frontend app. This is easier to teach, run, debug, and deploy than microservices.

Alternative considered: split agent, metrics, and chart services into separate services. Rejected for the first version because it adds deployment and networking overhead without improving the classroom goal.

### Decision: Use deterministic Java tools for business data

The agent MUST call typed business tools instead of generating SQL. Tools delegate to services that validate parameters, apply data scope, and compute metrics.

Alternative considered: Text-to-SQL. Rejected because it is less safe for enterprise training and makes permissions and metric definitions hard to guarantee.

### Decision: Keep existing chat routes

The backend should keep `/agent/chat`, `/agent/chat/stream`, and `/agent/session/{sessionId}` unless a strong reason appears during implementation. This lets the frontend remain simple while the domain changes.

Alternative considered: versioned API rewrite. Rejected for MVP because endpoint shape is not the teaching focus.

### Decision: Use original cross-border schema and seed data

The sales tables will be replaced with cross-border commerce tables: stores, operators, SKUs, orders, refunds, ad campaigns, ad daily reports, reviews, listings, and chat memory.

Alternative considered: keep sales schema and only rename labels. Rejected because it does not create an independent course asset and limits the new business story.

### Decision: Prefer structured visual payloads

The agent should return chart data through a stable visual payload contract. The frontend renders charts from structured data rather than guessing from free-form prose.

Alternative considered: let the model generate arbitrary ECharts JSON in text. Rejected because it is fragile and harder to validate.

### Decision: First version uses seeded local data

Marketplace data is represented by SQL seed data. Real SP-API or ad API integration can be an advanced chapter after the core teaching path is stable.

Alternative considered: integrate real Amazon SP-API immediately. Rejected because OAuth, rate limits, app approval, and account permissions would distract from Java AI engineering.

## Risks / Trade-offs

- **Risk:** Cross-border e-commerce scope grows too broad. → **Mitigation:** First MVP is limited to orders, ads, refunds, reviews, listings, and charts.
- **Risk:** LLM output may ignore chart payload instructions. → **Mitigation:** Tool returns structured payloads and tests verify parseable output.
- **Risk:** Students confuse platform-specific policy with software architecture. → **Mitigation:** Use fictional sample data and clearly label marketplace integrations as simulated.
- **Risk:** Keeping existing routes may hide domain refactoring work. → **Mitigation:** Rename internal modules and frontend copy while preserving only integration endpoints.
- **Risk:** Authentication and role scope can become too complex. → **Mitigation:** Use three teaching roles only: operator, store manager, operations director.

## Migration Plan

1. Freeze original copied directories as the working baseline.
2. Rename backend application/domain classes into cross-border commerce concepts.
3. Replace SQL schema and seed data with original cross-border sample data.
4. Replace tools and services with operations metrics, ads, refunds, reviews, listing, and chart payload capabilities.
5. Update frontend branding, role labels, quick questions, chart rendering, and demo flows.
6. Add smoke checks and a demo-question verification list.
7. Run backend tests and frontend build before declaring the MVP ready.

Rollback is simple during development: revert changes inside `crossborder-ops-agent` or restore from the copied `backend` and `frontend` baseline. No external demo project is affected.

## Open Questions

- Use LangChain4j as the only first-version agent framework, or add Spring AI examples later as a comparison chapter?
- Keep Vue for the course frontend or later provide a React/Next.js optional version?
- Should first-version persistence use MySQL like the copied project or PostgreSQL for easier future pgvector/RAG extension?
