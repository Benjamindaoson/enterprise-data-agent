## Why

The current copied project is still a sales-analysis demo. We need to turn it into an independent course-grade capstone project: a Java AI agent that demonstrates a real enterprise workflow without depending on the original course project's business model or code identity.

This change creates a focused MVP for a cross-border e-commerce operations analysis agent. It keeps the proven teaching loop of chat, tool calling, database-backed metrics, streaming response, and chart rendering, while replacing the domain with original cross-border commerce data and workflows.

## What Changes

- Reposition the application as `Cross-border E-commerce Operations Agent`.
- Replace sales-region, sales-rep, and sales-order domain concepts with stores, operators, SKUs, orders, refunds, ad campaigns, reviews, and listings.
- Provide an AI chat experience that can answer operational questions using deterministic Java tools instead of free-form SQL generation.
- Support streaming responses from the backend to the frontend.
- Generate chart payloads for operational metrics such as sales trend, profit trend, ACOS, ROAS, refund rate, and store comparisons.
- Add listing optimization capability for marketplace product title, bullet points, keywords, and localized copy.
- Add review insight capability to summarize negative review themes and operational risks.
- Keep the project scoped to the copied `backend` and `frontend` folders; no other demo projects are changed.
- Preserve a simple classroom-friendly deployment path with seeded sample data and repeatable demo questions.

## Capabilities

### New Capabilities
- `crossborder-chat-agent`: Chat-based AI agent that routes user questions to cross-border commerce tools and returns natural language answers.
- `operations-metrics`: Deterministic metrics for store, SKU, order, refund, advertising, and review analysis.
- `visual-payloads`: Structured chart payloads that the frontend can render without parsing arbitrary model prose.
- `listing-optimization`: AI-assisted listing generation and localization for cross-border marketplace products.
- `operator-access-scope`: Role-aware data scope for operator, store manager, and operations director personas.
- `course-demo-readiness`: Seed data, demo questions, and verification checks for classroom use.

### Modified Capabilities

None. This is the first OpenSpec change for the isolated project.

## Impact

- Affected backend areas: agent prompt/configuration, tool layer, service layer, repositories, entities, SQL schema/data, controllers, memory, and security context.
- Affected frontend areas: branding, navigation labels, quick questions, chat copy, role labels, chart rendering protocol, and demo workflows.
- APIs should keep the existing chat entry points where practical so the frontend/backend integration remains simple:
  - `POST /agent/chat`
  - `POST /agent/chat/stream`
  - `DELETE /agent/session/{sessionId}`
- Dependencies should stay close to the copied project for the first MVP: Spring Boot, LangChain4j, JPA, database, SSE, Vue, Pinia, Element Plus, and ECharts.
