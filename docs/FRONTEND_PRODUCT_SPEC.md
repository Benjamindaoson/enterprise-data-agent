# Enterprise Intelligence Workspace — Frontend Product Specification

> Status: Frozen frontend product baseline v0.1  
> Date: 2026-09-02  
> Scope: Iowa single-domain Enterprise Intelligence Workspace  
> Relationship: This specification defines the user experience and frontend acceptance criteria. It is used together with `full-product-completion-specification.md`.

## 0. Product intent

The application is an AI-assisted analytical workspace, not a generic chat page
and not a collection of disconnected dashboards. The primary user journey is:

```text
Business question
  → resolved context
  → plan and investigation
  → governed result
  → evidence-backed finding
  → follow-up or report
```

The frontend must make that journey visible and operable. Every visible finding
must have a path to its evidence. Every actionable chart element must lead to a
real filter, drill-down, investigation, or record view.

The frontend is not allowed to invent metrics, statuses, validation results, or
causal explanations. It renders backend contracts and clearly labels unavailable
or partial information.

## 1. Information architecture

The application has six first-level navigation areas:

```text
Enterprise Intelligence Workspace
├── Today
├── Analyses
│   ├── New Analysis
│   ├── Analysis Workspace
│   ├── Investigation
│   ├── Dashboard
│   ├── Evidence
│   ├── Report
│   └── History
├── Data
├── Semantics
├── Evaluation
└── Settings
```

The seven Analysis subareas are task-oriented views, not seven unrelated
products. A task ID, dataset version, and current task state remain visible
whenever a user is inside an analysis.

## 2. Design references and borrowing rules

The product uses established interaction patterns as references:

- [ThoughtSpot Spotter](https://www.thoughtspot.com/product/agents/spotter) for
  natural-language analysis, verified insights, and follow-up questions;
- [Hex](https://hex.tech/) for an analysis canvas where process and result live
  together;
- [Sigma](https://www.sigmacomputing.com/product/business-intelligence) for
  contextual exploration, breadcrumbs, and drill-down;
- [Metabase](https://www.metabase.com/product) for simple filters, tables,
  visual exploration, and drill-through;
- [Ant Design Pro](https://github.com/ant-design/ant-design-pro) for enterprise
  layout and page patterns, without cloning its application shell;
- [Ant Design X](https://ant-design-x.antgroup.com/components/introduce) for
  AI interaction primitives such as prompts, sources, sender, and streaming;
- [shadcn/ui dashboard blocks](https://ui.shadcn.com/examples/dashboard) and
  [Tremor](https://tremor.so/) for optional visual references only.

Borrow interaction patterns and information hierarchy. Do not copy proprietary
logos, illustrations, CSS, copy, or distinctive branded layouts. Any reused code
must be checked for license compatibility before inclusion.

## 3. Frontend technology boundary

The frontend is an independent Vite application in its own frontend package.
It must use:

```text
React
TypeScript
Vite
Ant Design 6
@ant-design/pro-components
Ant Design X
Apache ECharts
TanStack Query
Zustand
```

Do not clone the Ant Design Pro repository. Use Ant Design and the independent
component packages inside our own application architecture. The backend remains
the source of truth for task, semantic, evidence, and artifact contracts.

Required frontend boundaries:

```text
frontend/src/
├── app/              # router, providers, layout, error boundary
├── pages/            # route-level product pages
├── features/         # analysis, investigation, dashboard, evidence
├── components/       # reusable UI components
├── api/              # typed API client and query keys
├── stores/           # local view state only
├── design-system/    # tokens and primitives
└── test/             # unit, integration, Playwright helpers
```

The frontend may not contain business metric formulas, permission decisions,
data joins, or fabricated fallback results.

## 4. Design principles

### 4.1 Visual principles

- White or very light gray canvas;
- dark charcoal text;
- one restrained teal accent;
- compact, high information density;
- thin borders and minimal shadows;
- charts, tables, and values are the visual focus;
- restrained status colors with consistent meaning;
- generous whitespace around major sections, compact spacing inside data blocks.

### 4.2 Explicit prohibitions

- no large blue-purple gradients;
- no glowing AI orb;
- no glassmorphism;
- no default Ant Design layout shipped without a product-specific system;
- no card around every line of content;
- no excessive rounded corners;
- no unexplained decorative colors;
- no giant “AI is thinking” panel;
- no hidden evidence behind a separate unrelated page;
- no dead buttons or fake drill-downs.

### 4.3 Content principles

- Use plain business language first and canonical metric names second;
- always show period and unit with a number;
- distinguish `FACT`, `INFERENCE`, and `RECOMMENDATION`;
- distinguish `PARTIAL`, `ABSTAINED`, `FAILED`, and `NOT AVAILABLE`;
- never label wholesale orders as consumer sales;
- never label wholesale spread as store profit;
- never label contribution as proven causation.

## 5. Design tokens

### 5.1 Color tokens

| Token | Value | Use |
| --- | --- | --- |
| `color.canvas` | `#F7F9FA` | Application background |
| `color.surface` | `#FFFFFF` | Panels and content surfaces |
| `color.text` | `#17212B` | Primary text |
| `color.textSecondary` | `#657681` | Supporting text |
| `color.border` | `#DDE5E8` | Dividers and panel borders |
| `color.brand` | `#087F78` | Primary action, active state, links |
| `color.brandSoft` | `#E5F3F1` | Selected/positive background |
| `color.info` | `#3478A8` | Informational state |
| `color.warning` | `#A56A12` | Partial, warning, needs attention |
| `color.warningSoft` | `#FFF2D9` | Warning background |
| `color.danger` | `#B5473D` | Failed, denied, negative change |
| `color.dangerSoft` | `#FBE9E7` | Error background |
| `color.chart.1` | `#087F78` | Primary series |
| `color.chart.2` | `#3478A8` | Comparison series |
| `color.chart.3` | `#A56A12` | Highlight/driver |
| `color.chart.4` | `#8E6BAF` | Secondary category |

Charts must not use arbitrary per-card colors. Positive/negative direction is
not the same as claim type and must not reuse claim colors ambiguously.

### 5.2 Typography and geometry

| Token | Value |
| --- | --- |
| Body font | Inter/system sans-serif |
| Display font | System sans-serif; no decorative serif for data pages |
| `font.size.xs` | 11px |
| `font.size.sm` | 12px |
| `font.size.md` | 14px |
| `font.size.lg` | 16px |
| `font.size.xl` | 20px |
| `font.size.display` | 28px |
| Base spacing | 4px |
| Common spacing | 8px, 12px, 16px, 24px, 32px |
| Panel radius | 8px |
| Control radius | 6px |
| Border | 1px solid `color.border` |
| Shadow | none by default; `0 4px 16px rgba(23,33,43,.08)` only for overlays |

### 5.3 Data formatting

- USD: `$1,234,567.89`;
- percentages: one decimal unless precision is material;
- bottles: integer with thousands separators;
- liters: one or two decimal places based on metric definition;
- negative values: minus sign and danger color only when direction is meaningful;
- every KPI includes label, value, period, comparison basis, and unit;
- unavailable values render `—` plus a reason, never zero.

## 6. Navigation and shell

```text
┌───────────────┬──────────────────────────────────────────────────────────┐
│ Brand         │ Breadcrumb / task context              User / data status │
├───────────────┼──────────────────────────────────────────────────────────┤
│ Today         │ Page title                              global actions   │
│ Analyses      │                                                        │
│ Data          │ Page content                                             │
│ Semantics     │                                                        │
│ Evaluation    │                                                        │
│ Settings      │                                                        │
│               │                                                        │
│ environment   │                                                        │
└───────────────┴──────────────────────────────────────────────────────────┘
```

Shell requirements:

- active navigation is always visible;
- current dataset status is visible in the header;
- current task context appears in Analysis views;
- global search is optional for v1 but must not replace navigation;
- navigation collapse is supported below 1100px;
- no page may depend on browser back to preserve unsaved analysis state.

## 7. Today page

### 7.1 Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Good morning                         Dataset READY · through 2026-07-31   │
│ What would you like to understand?                                      │
│ [ Ask a business question........................................ ] [→]  │
├──────────────────────────────────────────────────────────────────────────┤
│ [Sales] [Bottles] [Avg price] [Wholesale spread]                        │
├────────────────────────────────────┬─────────────────────────────────────┤
│ Suggested analyses                 │ Recent analyses                     │
│ • Compare July vs June             │ July sales by vendor     COMPLETED  │
│ • Find largest contributors         │ Spread by category       PARTIAL    │
│ • Explain price / volume / mix      │ Store drill-down         FAILED     │
├────────────────────────────────────┴─────────────────────────────────────┤
│ Data quality / freshness / limitations                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Required interactions

- Submit question → New Analysis with question prefilled;
- click suggestion → New Analysis with example loaded;
- click recent analysis → reopen Analysis Workspace;
- click dataset status → Data Status;
- click KPI → Dashboard scoped to that metric and default period.

## 8. New Analysis page

### 8.1 Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ New analysis                                      [Cancel]                │
│ [Business question textarea...........................................]  │
│ Examples: [July vs June] [Top vendors] [PVM] [Spread]                    │
├────────────────────────────────────┬─────────────────────────────────────┤
│ Question                            │ Resolved request                    │
│                                    │ Metric: Wholesale Sales             │
│                                    │ Period: Jul 2026                    │
│                                    │ Compare: Jun 2026                   │
│                                    │ Grain: Vendor                       │
│                                    │ Warnings: none                      │
├────────────────────────────────────┴─────────────────────────────────────┤
│ [Need clarification] or [Start analysis]                                │
└──────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Required behavior

- show parsed metric, period, comparison, dimensions, and filters;
- show data limitations before execution;
- if ambiguity changes the answer, block execution and ask clarification;
- show the exact resolved dates, never only “last month”;
- Start Analysis creates a task and navigates to its workspace;
- unsupported profit questions explain the supported wholesale alternative.

## 9. Analysis Workspace

This is the primary product screen.

### 9.1 Wireframe

```text
┌────────────────┬──────────────────────────────────────────┬────────────────┐
│ Analysis nav   │ Analysis Workspace                       │ Evidence       │
│                │                                          │ Inspector      │
│ Overview       │ Question                                 │                │
│ Context        │ Status · Dataset · Period · Scope        │ CLAIM          │
│ Plan           │                                          │ type / status  │
│ Investigation  │ Analysis Plan                            │                │
│ Dashboard      │ [1 baseline] [2 drivers] [3 verify]      │ EVIDENCE       │
│ Findings       │                                          │ observation    │
│ Report         │ Investigation timeline / findings         │ calculation    │
│                │                                          │ dataset/version│
│                │ Dynamic BI                               │ validation     │
│                │                                          │                │
└────────────────┴──────────────────────────────────────────┴────────────────┘
```

### 9.2 Required interactions

- click a plan step → focus the corresponding observation or event;
- click a hypothesis → open Investigation view filtered to that hypothesis;
- click KPI/chart/table finding → open Evidence Inspector;
- click driver → offer View Records, Filter, Break Down, Investigate with AI,
  and View Evidence;
- click “Investigate with AI” → create authorized follow-up task;
- click Report → open report view without losing task context;
- click dataset/version → open Data Status or Semantic Explorer detail.

### 9.3 Evidence Inspector

```text
CLAIM
Vendor X was the largest observed contributor…

Type             INFERENCE
Status           SUPPORTED / QUALIFIED
Impact           -$1.24M · 31.6% of observed decline

EVIDENCE
Observation #128
Query / Computation #SQL-53

METRIC           Wholesale Sales v1.2
PERIOD           Jul 2026 vs Jun 2026
DATASET          iowa_liquor_snapshot_2026_07_v1

VALIDATION       ✓ Metric  ✓ Time  ✓ Join  ✓ Reconciliation  ✓ Freshness

[Investigate further] [Open result] [Copy reference]
```

The inspector must never display a validation check unless the backend has
returned a corresponding validation result.

## 10. Investigation page

### 10.1 Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Investigation · July sales change                         [Follow up]    │
├──────────────────────┬───────────────────────────────┬───────────────────┤
│ Hypotheses            │ Timeline                      │ Selected evidence │
│ ✓ Quantity            │ Baseline computed             │ Claim             │
│ ? Unit price          │ Top contributors ranked       │ Observation       │
│ ? Product mix         │ Reconciliation passed        │ Validation        │
│                      │                               │                   │
│ Status legend         │ [Open next step]              │                   │
└──────────────────────┴───────────────────────────────┴───────────────────┘
```

Required states are `PROPOSED`, `TESTING`, `SUPPORTED`, `REJECTED`, and
`INCONCLUSIVE`. The UI must not infer a hypothesis state from prose.

## 11. Dynamic BI page

### 11.1 Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Dashboard   [Period] [Compare] [Metric] [Dimension] [Filters] [Reset]    │
├──────────────────────────────────────────────────────────────────────────┤
│ KPI 1             KPI 2             KPI 3             KPI 4                │
├───────────────────────────────────┬──────────────────────────────────────┤
│ Trend + MoM / YoY                  │ Contribution / Waterfall             │
├───────────────────────────────────┴──────────────────────────────────────┤
│ Price / Volume / Mix                                                     │
├──────────────────────────────────────────────────────────────────────────┤
│ [Category] [Vendor] [Store] [County]                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ Detail table: sortable, filterable, paginated, exportable                │
└──────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Chart action menu

Every interactive chart element must support applicable actions:

```text
View records
Filter by this value
Break down by another dimension
Investigate with AI
View supporting evidence
```

Charts must show title, metric, unit, selected period, comparison period,
legend, tooltip, empty state, and data source/version. A chart click that only
changes frontend text is not a valid drill-down.

## 12. Evidence page

### Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Evidence library        [Claim type] [Status] [Metric] [Search]          │
├───────────────────────────────┬──────────────────────────────────────────┤
│ Claim list                     │ Evidence detail                         │
│ FACT · sales increased         │ Claim / relation                        │
│ INFERENCE · Vendor X driver   │ Observation / execution                  │
│ QUALIFIED · mix residual      │ Query or computation / parameters         │
│                               │ Snapshot / semantic / context versions  │
│                               │ Validation / limitations                 │
└───────────────────────────────┴──────────────────────────────────────────┘
```

No Evidence page may render a manually authored evidence record without a
backend provenance reference.

## 13. Report page

### Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Report                         [Markdown] [HTML] [Copy link] [Download]   │
├──────────────────────────────────────────────────────────────────────────┤
│ Executive Summary                                                         │
│ Business Performance                                                      │
│ Key Findings                                                              │
│ Driver Analysis                                                           │
│ Supporting Evidence                                                       │
│ Limitations                                                               │
│ Recommendations                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

The report view must show the same saved Claims and Evidence as the workspace.
It must not display a second independently generated narrative.

## 14. History page

### Wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Analysis history       [Search] [State] [Owner] [Date]                   │
├──────────────────────────────────────────────────────────────────────────┤
│ Task question                         State       Dataset       Updated   │
│ July sales by vendor                  COMPLETED   snapshot v1   today     │
│ Spread by category                    PARTIAL     snapshot v1   yesterday │
│ └─ Follow-up: top vendor              COMPLETED   snapshot v1   yesterday │
└──────────────────────────────────────────────────────────────────────────┘
```

Actions: reopen, view lineage, inspect evidence, create follow-up, and replay
when the backend confirms a real replayable checkpoint.

## 15. Data Status page

Must display:

- source publisher and source asset;
- snapshot ID and version;
- extracted/updated/freshness timestamps;
- business date range;
- row count and file/schema fingerprints;
- duplicate count;
- current Store/Product join coverage and reconciliation;
- metric availability windows;
- quality warnings and limitations;
- attribution/license metadata.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Snapshot READY · iowa_liquor_snapshot_2026_07_v1                        │
├───────────────┬──────────────┬──────────────┬────────────────────────────┤
│ Through date  │ Rows         │ Exact dupes  │ Curated hash               │
├───────────────┴──────────────┴──────────────┴────────────────────────────┤
│ Metric availability / quality checks / source references                  │
└──────────────────────────────────────────────────────────────────────────┘
```

## 16. Semantic Explorer

Must support browsing and detail views for:

- metric definition, formula, unit, availability, and caution;
- dimensions and grain;
- source mapping;
- Join Policy and cardinality;
- business rules;
- quality/freshness rules;
- semantic package version and fingerprint.

The explorer is read-only. It cannot silently change a metric definition.

## 17. Evaluation page

Must display:

- suite version and case count;
- latest run and historical runs;
- pass/fail by case;
- semantic, period/filter/grain, numeric, evidence, policy, runtime, and report
  metrics;
- failure category and failing stage;
- links from a failed case to its task trajectory;
- “not measured” when a metric was not actually computed.

No score may be displayed merely because cases loaded. Controlled fixtures must
be executed or explicitly marked `NOT RUN`; they must never be auto-passed.

## 18. Settings page

Must display:

- active model provider and provider version;
- credential status without exposing secrets;
- dataset and semantic package versions;
- query/tool/time/result-row budgets;
- runtime mode and worker capacity;
- feature flags and environment mode;
- link to governance and data limitations.

Settings that affect analysis must come from the backend configuration contract,
not hard-coded frontend labels.

## 19. System states

Every page and action must define applicable states:

| State | Required treatment |
| --- | --- |
| Loading | Skeleton or compact progress indicator preserving page structure |
| Empty | Explain why empty and provide a relevant next action |
| Error | Human-readable message, error category, retry or recovery action |
| Clarification | Blocking question with answer input and context |
| Partial | Show available result, explicit limitation, and next option |
| Abstain | Explain unsupported conclusion and supported alternative |
| Failed | Show stage, reason, trace/reference, and retry/restart option where safe |
| Cancelled | Preserve task history and show restart/follow-up option |
| Model unavailable | Offer deterministic/manual fallback only when valid; label it |
| Data unavailable | Block affected analysis and link to Data Status |
| Stale data | Show freshness warning before relying on results |

No state may be represented only by color. Status text and accessible labels are
required.

## 20. Click paths

### 20.1 Primary analysis path

```text
Today question
  → New Analysis
  → Resolved request
  → Start analysis
  → Workspace
  → Dashboard
  → Driver action
  → Evidence Inspector
  → Investigation / Follow-up
  → Report
```

### 20.2 Clarification path

```text
New Analysis
  → ambiguity detected
  → clarification form
  → submit answer
  → task resumes
  → workspace updates
```

### 20.3 Evidence path

```text
KPI / finding / chart point
  → Evidence Inspector
  → Observation
  → Query / Computation
  → Dataset / Semantic / Context
  → Validation
  → Investigate further
```

### 20.4 Failure path

```text
Task failure
  → failure stage and category
  → retry if transient
  → resume from checkpoint if available
  → otherwise start a new task without mutating the old one
```

## 21. Responsive rules

### Desktop: 1440px+

- three-column Workspace;
- persistent Evidence Inspector;
- full data tables and chart legends;
- 12-column content grid;
- target screenshot viewport: 1440×900.

### Tablet: 768–1439px

- two-column Workspace;
- Evidence Inspector becomes a right drawer;
- filters wrap into two rows;
- tables preserve horizontal scroll and key columns.

### Mobile: below 768px

- single-column flow;
- Evidence Inspector becomes a bottom sheet or dedicated detail route;
- charts may simplify but cannot lose metric, unit, period, or source;
- tables become cards or horizontal-scroll tables;
- primary action remains reachable without scrolling to the page bottom.

## 22. Accessibility and interaction quality

- keyboard navigation for all actions;
- visible focus state;
- semantic labels for chart summaries and status badges;
- color is never the only encoding;
- minimum contrast suitable for enterprise use;
- tables expose headers and sort state;
- async actions announce progress and completion;
- destructive or irreversible actions require confirmation;
- focus moves into drawers/dialogs and returns to the triggering control.

## 23. Screenshot acceptance

Every product area must have a screenshot review at 1440×900 and a responsive
review at 390×844. Acceptance requires:

- no blank or placeholder page;
- no dead button;
- no overflow or clipped primary content;
- no unexplained color or decorative gradient;
- correct metric names, units, periods, and status labels;
- correct loading, empty, error, partial, and unavailable states;
- chart title, tooltip, legend, and source/version visible where applicable;
- Evidence Inspector opens from every important finding;
- report is viewable and exportable;
- no browser console errors.

## 24. Frontend test requirements

### Unit and component tests

- number/date/status formatters;
- claim and evidence badges;
- filter state serialization;
- chart action menu;
- Evidence Inspector;
- system-state components;
- route guards and task context.

### Integration tests

- New Analysis → API task creation;
- task polling/SSE state updates;
- chart drill-down request;
- Evidence Inspector data loading;
- clarification resume;
- follow-up creation;
- report loading/export;
- failed task recovery.

### Playwright flows

At minimum:

1. Create and complete a sales-by-vendor analysis;
2. Inspect a finding's Evidence Inspector;
3. Drill down from Dashboard to a dimension detail;
4. Ask an unsupported profit question and see clarification;
5. Submit clarification and resume;
6. Create an authorized follow-up;
7. Open History and reopen a task;
8. View Data Status and Semantic Explorer;
9. Run Evaluation and inspect a failed case;
10. Render loading, empty, partial, failed, cancelled, and unavailable states.

### Screenshot regression

Screenshots are captured for Today, New Analysis, Workspace, Dashboard,
Evidence, Report, History, Data Status, Semantic Explorer, Evaluation, and
Settings in light desktop and responsive modes.

## 25. Definition of Done

The frontend is complete only when:

1. all six first-level navigation areas and all Analysis subareas are routable;
2. every page has a real backend data contract;
3. every important finding opens a real Evidence Inspector;
4. chart actions trigger real backend filters/drill-down/follow-up operations;
5. loading, empty, error, partial, abstain, failed, cancelled, and unavailable
   states are implemented where applicable;
6. all ten Playwright flows pass;
7. screenshot acceptance passes at 1440×900 and mobile dimensions;
8. no metric, permission, provenance, or validation logic is invented in the UI;
9. the frontend is integrated with the Product Feature Master Matrix and each
   applicable frontend cell can be marked `PASS`.
