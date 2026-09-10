# Student Training Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the runnable Crossborder Ops Agent MVP into a student hands-on training project.

**Architecture:** Keep the existing Spring Boot backend and Vue frontend unchanged for this phase. Add course materials, guided labs, and a smoke-check script around the working system so students can run, inspect, modify, and verify one feature at a time.

**Tech Stack:** Java 21, Spring Boot 3.5, LangChain4j, MySQL, Redis, Vue 3, Pinia, Element Plus, ECharts, PowerShell.

## Global Constraints

- Keep edits inside `crossborder-ops-agent`.
- Do not add dependencies for course materials.
- Do not change the already verified backend/frontend runtime path.
- Treat real marketplace APIs, RAG, MCP, and multi-agent orchestration as extension chapters, not first lab requirements.
- Keep student tasks small enough to finish in one class session.

---

### Task 1: Course Entry Point

**Files:**
- Create: `course/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: Existing app URLs `http://127.0.0.1:5173` and `http://127.0.0.1:8087`.
- Produces: A clear student entry point and route map.

- [x] **Step 1: Add `course/README.md`**

Create a course index that explains learning goals, project map, run commands, and lab order.

- [x] **Step 2: Link the course index from `README.md`**

Add a short "学生实训入口" section near the top.

- [x] **Step 3: Verify the docs render as plain Markdown**

Run: `Get-Content -Raw -Encoding UTF8 course\README.md`

Expected: Chinese text is readable.

### Task 2: Guided Labs

**Files:**
- Create: `course/labs/01-run-and-observe.md`
- Create: `course/labs/02-read-agent-tool-service.md`
- Create: `course/labs/03-add-business-metric.md`
- Create: `course/labs/04-add-chart-question.md`
- Create: `course/labs/05-extension-csv-import.md`

**Interfaces:**
- Consumes: Existing backend packages under `backend/src/main/java/com/jichi/salesAgent`.
- Produces: Five ordered student exercises.

- [x] **Step 1: Write Lab 01**

Focus on startup, login, and smoke check.

- [x] **Step 2: Write Lab 02**

Focus on tracing chat -> agent -> tool -> service -> repository -> database.

- [x] **Step 3: Write Lab 03**

Focus on adding one metric with test-first discipline.

- [x] **Step 4: Write Lab 04**

Focus on adding one chart scenario with `VISUAL_PAYLOAD`.

- [x] **Step 5: Write Lab 05**

Keep CSV import as an extension, not a required MVP change.

### Task 3: Student Verification

**Files:**
- Create: `course/demo-questions.md`
- Create: `course/assessment.md`
- Create: `course/scripts/smoke-check.ps1`

**Interfaces:**
- Consumes: Backend endpoints `/actuator/health`, `/auth/login`, `/test/tool/business-summary`, `/test/tool/business-trend-chart`.
- Produces: A repeatable way to check the local training environment.

- [x] **Step 1: Add demo question checklist**

List the ten classroom questions and expected capability under each one.

- [x] **Step 2: Add assessment rubric**

Grade students by runnable project, correct metric change, tool integration, chart output, and explanation quality.

- [x] **Step 3: Add PowerShell smoke check**

Use built-in `Invoke-RestMethod`; no new dependency.

- [x] **Step 4: Run the smoke check**

Run: `powershell -ExecutionPolicy Bypass -File course\scripts\smoke-check.ps1`

Expected: health, login, summary, and chart checks pass.
