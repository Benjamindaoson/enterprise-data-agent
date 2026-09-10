## 1. Requirements and Scope

- [x] 1.1 Confirm MVP positioning as a cross-border e-commerce operations analysis agent.
- [x] 1.2 Finalize supported first-version user roles: operator, store manager, operations director.
- [x] 1.3 Finalize the first-version demo questions and reject out-of-scope questions.
- [x] 1.4 Document first-version non-goals: real marketplace APIs, MCP, multi-agent orchestration, and RAG.

## 2. Domain and Data Model

- [x] 2.1 Replace sales-domain entities with cross-border entities for stores, operators, SKUs, orders, refunds, ads, reviews, listings, and chat memory.
- [x] 2.2 Rewrite `schema.sql` for the new cross-border commerce tables.
- [x] 2.3 Rewrite `data.sql` with original demo data that supports trends, rankings, refunds, ad anomalies, and negative review insights.
- [x] 2.4 Update repositories for the new domain model and remove unused sales repositories.

## 3. Backend Metrics and Tools

- [x] 3.1 Implement deterministic order and profit metric services.
- [x] 3.2 Implement refund-rate and high-risk SKU analysis.
- [x] 3.3 Implement advertising metrics for ACOS, ROAS, spend, and sales.
- [x] 3.4 Implement negative review theme analysis from stored review data.
- [x] 3.5 Implement listing generation and localization tool behavior.
- [x] 3.6 Implement structured chart payload generation for line and bar charts.
- [x] 3.7 Apply role data scope in service-layer queries.

## 4. Agent Integration

- [x] 4.1 Replace the sales agent interface and system prompt with a cross-border operations agent.
- [x] 4.2 Register the new tool set with the LangChain4j agent configuration.
- [x] 4.3 Keep synchronous and streaming chat endpoints compatible with the frontend.
- [x] 4.4 Preserve session memory while renaming domain-facing classes and copy.
- [x] 4.5 Handle unsupported questions with clear limitation messages.

## 5. Frontend Experience

- [x] 5.1 Rebrand the UI as a cross-border e-commerce operations assistant.
- [x] 5.2 Replace quick questions and welcome cards with cross-border demo scenarios.
- [x] 5.3 Replace role labels with operator, store manager, and operations director labels.
- [x] 5.4 Update chart parsing/rendering to use the structured visual payload contract.
- [ ] 5.5 Add listing preview rendering if listing output is returned.
- [x] 5.6 Verify streaming chat still works after backend changes.

## 6. Verification

- [x] 6.1 Add backend tests for metrics services using seeded or test data.
- [ ] 6.2 Add backend tests for role scope filtering.
- [x] 6.3 Add backend tests or smoke checks for tool outputs and chart payload validity.
- [x] 6.4 Build the frontend successfully.
- [ ] 6.5 Run the prepared demo question set and record expected outputs.

## 7. Security and Configuration

- [x] 7.1 Move model keys and database credentials to environment variables or local-only ignored configuration.
- [x] 7.2 Ensure the demo login path is clearly marked as classroom-only unless real auth is implemented.
- [ ] 7.3 Validate tool inputs for dates, store identifiers, locale, chart type, and top-N limits.
- [x] 7.4 Log tool calls with safe parameter summaries and without leaking secrets.

## 8. Delivery and Course Materials

- [x] 8.1 Add a project README with setup, run commands, and demo accounts.
- [x] 8.2 Add a classroom walkthrough covering chat, tool calling, charts, listing, and ad anomaly analysis.
- [x] 8.3 Add a final demo script with 10 prepared questions.
- [x] 8.4 Document extension chapters: RAG compliance check, MCP, multi-agent orchestration, local model deployment, and real marketplace API integration.
