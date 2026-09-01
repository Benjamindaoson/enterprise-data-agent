# Enterprise Intelligence Workspace：核心模块设计

> Status: Module Design Baseline v0.3  
> Date: 2026-09-01  
> Parent: [架构与开发基线](architecture-development-baseline.md)  
> Scope: 模块职责、输入输出、内部端口、公共 API、数据流与失败行为

数据决策依据：[ADR-001：MVP 主数据集与双轨评测数据策略](adr/ADR-001-primary-demo-dataset.md)
数据实施契约：[MVP 数据基础冻结设计](data-foundation-design.md)

## 0. 设计结论

系统采用 Modular Monolith + Durable Agent Runtime：

> 一个 Analytical Orchestrator，通过结构化领域对象调用企业上下文、受治理执行、证据和验证模块。

不采用多个 Agent 自由对话，也不将每个内部模块暴露为 HTTP 服务。

本设计对前置草案做出以下关键修正：

- Context 不是 Plan 之后的一次性步骤，而是 Bootstrap、Plan、Step 三阶段编译。
- Workspace 只暴露面向用户的 Task Resource API；Planner、Context、Tool、Evidence、Verification 使用进程内类型化端口。
- Evidence 不能由客户端任意创建，必须由受治理执行和验证流程自动捕获。
- SQL Tool 接收已解析的语义查询请求或受约束查询计划，不直接把自然语言当作可执行 SQL。
- Runtime 不重复进行业务任务拆解，只调度 Analysis Plan 和 Investigation Decision。
- Enterprise Data Connectivity 是正式模块；Evaluation、Observability、Security 是横向能力。
- `profit` 不作为 MVP 的默认语义对象；Iowa 数据只能提供明确的 `wholesale_gross_spread` 批发价差，用户询问门店或会计利润时必须澄清数据边界。

---

## 1. 运行拓扑

```text
User
  ↓
Analysis Workspace / Public Task API
  ↓
AnalysisTask Created
  ↓
Bootstrap Context Compiler
  ↓
Business Intent Resolution ── ambiguity ──→ Clarification
  ↓
Analysis Planner + Initial Hypotheses
  ↓
Plan Context Compiler
  ↓
Durable Runtime
  ↓
Step Context Compiler
  ↓
Governed Tool Request
  ↓
Policy Check → Data Connector → SQL/Analysis Tool
  ↓
Execution Result → Observation → Evidence Capture
  ↓
Verification → Hypothesis Update → Next Investigation Decision
  ↑                                      ↓
  └────────────── continue ──────────────┘
                                         ↓ stop
                              Claim and Artifact Composer
                                         ↓
                              Workspace / Chart / Report
```

### 1.1 三阶段 Context Compilation

| 阶段 | 目的 | 主要输入 | 主要输出 |
| --- | --- | --- | --- |
| `BOOTSTRAP` | 正确理解问题并发现歧义 | 用户、问题、领域入口、权限 | 候选指标、术语、时间解释、可见范围 |
| `PLAN` | 为分析计划提供领域约束 | Business Intent、初始假设、语义包 | 指标依赖、允许维度、Join Policy、数据质量、工具能力 |
| `STEP` | 为单个执行步骤提供最小上下文 | Analysis Step、当前假设、Runtime State | 允许数据对象、查询边界、工具参数、预算、验证要求 |

每个 Context Package 不可变、可版本化，并记录其输入来源。后续上下文变化创建新版本，不原地覆盖历史版本。

---

## 2. 模块边界总览

| 模块 | 负责 | 不负责 |
| --- | --- | --- |
| Analysis Workspace | Task 创建、进度、调查、证据、报告、反馈 | 业务推理、SQL、证据写入 |
| Analytical Intelligence | Intent、Plan、Hypothesis、Investigation Decision、Claim Synthesis | 可靠调度、数据库访问、权限判断 |
| Enterprise Context Intelligence | 语义资产、权限感知 Context Compilation | 执行 SQL、管理任务生命周期 |
| Agent Runtime | 状态、调度、预算、恢复、重放 | 定义指标、形成业务真相 |
| Governed Analysis Execution | 查询和确定性分析执行 | 自主决定业务目标、生成无证据结论 |
| Evidence & Artifact | Observation、Evidence、Validation、Claim、Artifact | 任意外部写证据、重新执行分析计划 |
| Enterprise Data Connectivity | 源连接、Schema、查询下推、源身份传播 | 企业语义定义、报告生成 |
| Governance | 身份、授权、策略、审计 | 由 Prompt 决定权限 |
| Evaluation & Observability | Trace、评分、回归、失败分类 | 参与生产结论形成 |

---

## 3. Module 1：Analysis Workspace

### 3.1 职责

- 创建和查看 Analysis Task；
- 收集必要澄清；
- 展示结构化 Plan 和当前进度；
- 展示 Hypothesis 状态和 Investigation Timeline；
- 展示 Claim、Evidence、Validation 和限制条件；
- 展示 Chart/Report Artifact；
- 收集用户反馈和专家纠正。

### 3.2 输入

`CreateAnalysisTaskCommand`：

- `question`
- 可选 `scope_hint`
- `user_context`
- `domain_hint`
- 可选 `comparison_hint`

用户输入只作为提示。最终指标、时间、范围和比较基线必须经过语义解析。

`CreateFollowUpTaskCommand`：

- `parent_task_id`
- `question`
- 可选 `referenced_claim_ids` / `referenced_evidence_ids`
- 由 API 注入的当前可信 `user_context`

已完成任务上的追问创建新的子 Task。父 Task 的 Context、Plan、Claim、Evidence 和 Artifact 保持不可变；Context Compiler 重新检查当前权限、数据/语义版本和证据分类后，决定哪些资产可以复用。

### 3.3 输出

- `AnalysisTaskSummary`
- `AnalysisPlanView`
- `InvestigationTimeline`
- `ClaimView[]`
- `EvidenceView[]`
- `ArtifactView[]`
- `ClarificationRequest`

### 3.4 公共 API

MVP 只冻结面向用户的 Resource API：

| Method | Path | 用途 |
| --- | --- | --- |
| `POST` | `/api/v1/analysis-tasks` | 创建任务 |
| `POST` | `/api/v1/analysis-tasks/{task_id}/follow-ups` | 创建关联父任务的深度追问子任务 |
| `GET` | `/api/v1/analysis-tasks/{task_id}` | 获取任务摘要和状态 |
| `POST` | `/api/v1/analysis-tasks/{task_id}/clarifications` | 回答必要澄清 |
| `POST` | `/api/v1/analysis-tasks/{task_id}/cancel` | 取消任务 |
| `GET` | `/api/v1/analysis-tasks/{task_id}/events` | 通过 SSE 获取进度事件 |
| `GET` | `/api/v1/analysis-tasks/{task_id}/plan` | 获取结构化计划 |
| `GET` | `/api/v1/analysis-tasks/{task_id}/investigation` | 获取假设和调查时间线 |
| `GET` | `/api/v1/analysis-tasks/{task_id}/claims` | 获取结论列表 |
| `GET` | `/api/v1/analysis-tasks/{task_id}/evidence/{evidence_id}` | 获取证据详情 |
| `GET` | `/api/v1/analysis-tasks/{task_id}/artifacts` | 获取图表和报告 |
| `POST` | `/api/v1/analysis-tasks/{task_id}/feedback` | 提交用户/专家反馈 |

以下能力不暴露为公共 API：Business Understanding、Plan 生成、Context Compile、Tool Select、Evidence Write、Verification Run。

### 3.5 安全约束

- API 层创建可信 `UserContext`，不接受客户端伪造角色或权限集合。
- 返回的 Task、Evidence、Artifact 必须再次执行对象级访问检查。
- SSE 只输出用户可见事件，不输出模型原始思维链、密钥、完整敏感数据或内部 Prompt。

---

## 4. Module 2：Analytical Intelligence Engine

### 4.1 职责

- Business Understanding；
- Analysis Planning；
- Hypothesis Lifecycle；
- Investigation Decision；
- Claim/Recommendation Synthesis。

### 4.2 子模块与内部端口

#### Intent Resolver

输入：

- `AnalysisTask`
- `BootstrapAnalysisContext`

输出：

- `ResolvedBusinessIntent`，或
- `ClarificationRequest`

`ResolvedBusinessIntent` 至少包含：

- objective；
- metric IDs and versions；
- scope；
- time range；
- comparison baseline；
- requested output；
- unresolved assumptions。

内部端口：`resolve_intent(task, bootstrap_context)`。

#### Analysis Planner

输入：

- `ResolvedBusinessIntent`
- `PlanAnalysisContext`
- `TaskBudget`

输出：

- `AnalysisPlan`
- initial `Hypothesis[]`

内部端口：`create_plan(intent, context, budget)`。

#### Investigation Policy

输入：

- 当前 `AnalysisState`
- `Hypothesis[]`
- 最新 `Observation[]`
- `ValidationResult[]`
- 剩余预算

输出 `InvestigationDecision`：

- `EXECUTE_STEP`
- `REFINE_PLAN`
- `REQUEST_CLARIFICATION`
- `SYNTHESIZE`
- `COMPLETE_PARTIAL`
- `STOP_FAILED`

内部端口：`decide_next(state)`。

#### Claim Synthesizer

输入：

- 已验证 Observation；
- Hypothesis 状态；
- Evidence 关系；
- 领域措辞规则。

输出：

- `FACT`、`INFERENCE`、`RECOMMENDATION` 类型的 Claim；
- 限制条件；
- 未排除的替代解释。

内部端口：`synthesize_claims(verified_state)`。

### 4.3 禁止行为

- 不从聊天历史恢复唯一状态；
- 不将模型自报 confidence 当作可信度；
- 不绕过 Context Compiler 自行选择表和字段；
- 不把相关性描述为已证明因果；
- 不在预算耗尽或关键验证失败后继续无限调查。

---

## 5. Module 3：Enterprise Context Intelligence

### 5.1 职责

- 管理版本化 Domain Semantic Package；
- 聚合 Schema、Lineage、Quality、Freshness 和 Policy 元数据；
- 解析业务术语和指标候选；
- 编译 permission-aware、task-specific Context Package；
- 为 Context 提供来源和版本追踪。

### 5.2 输入

`ContextCompileRequest`：

- `stage`: `BOOTSTRAP | PLAN | STEP`
- `task_id`
- `user_context`
- `question` 或 `analysis_step`
- 可选 `resolved_intent`
- 可选 `hypothesis_ids`
- `domain_version`
- `budget`

### 5.3 输出

`AnalysisContext`：

- context ID/version/hash；
- resolved metrics/dimensions/entities；
- time and grain semantics；
- allowed sources/tables/columns；
- allowed join paths and cardinalities；
- business rules；
- quality/freshness warnings；
- available tools；
- query/resource constraints；
- source references。

### 5.4 内部端口

- `compile_context(request)`
- `resolve_metric(term, domain, user_context)`
- `get_metric(metric_id, version)`
- `get_schema(source_id, version)`
- `get_allowed_join_paths(metric_ids, dimensions, user_context)`

### 5.5 失败行为

| 情况 | 行为 |
| --- | --- |
| 多个指标候选会改变结果 | 返回 Clarification，不静默选择 |
| 指标不存在 | 返回 Unsupported Semantic Error |
| 用户无权访问必要指标/维度 | 返回 Policy Denial；任务拒绝或降级 |
| 数据陈旧 | Context 加入 Freshness Warning，交由计划和验证判断 |
| 无安全 Join Path | 阻止该分析步骤 |

---

## 6. Module 4：Agent Runtime

### 6.1 职责

- 启动、暂停、恢复和取消 Analysis Task；
- 依据 Plan、Investigation Decision 和状态机调度步骤；
- 持久化 checkpoint；
- 管理查询数、工具数、时间、token 和成本预算；
- 执行重试、超时和失败分类；
- 产生领域事件和 Trace。

### 6.2 输入

- `AnalysisTask`
- `AnalysisPlan`
- `AnalysisContextRef`
- `RuntimeCommand`: start/resume/cancel

### 6.3 输出

- `RuntimeState`
- `ToolExecutionRequest`
- `DomainEvent[]`
- terminal status

### 6.4 内部端口

- `start_task(task_id)`
- `resume_task(task_id, checkpoint_id, input)`
- `cancel_task(task_id)`
- `dispatch_step(step, step_context)`
- `persist_checkpoint(state)`

Tool Router 是 Runtime 内部的策略组件，不作为 LLM 服务或 HTTP 接口。它根据 `AnalysisStep.kind`、Context 中允许工具和 Policy 结果选择工具。

### 6.5 重试与幂等性

- 仅瞬时基础设施错误自动重试；
- 语义错误返回 Planner/Context，不做相同请求盲重试；
- SQL 修复最多执行预算允许的有限次数；
- Tool Call 必须具有 idempotency key；
- checkpoint 之前的外部读取可以重放，未来写操作必须独立审批且保证幂等；
- 恢复时不得重复写入同一 Observation/Evidence。

---

## 7. Module 5：Governed Analysis Execution

### 7.1 SQL Query Pipeline

```text
SemanticQueryRequest
  → Query Planner/Generator
  → SQL Parse
  → Policy Validation
  → Semantic Validation
  → Cost/Limit Check
  → Read-only Execution
  → Result Normalization
  → Observation Candidate
```

输入 `SemanticQueryRequest`：

- metric IDs/versions；
- dimensions；
- filters；
- time range；
- grain；
- comparison；
- allowed source and join refs；
- context ID；
- execution budget。

输出 `ExecutionResult`：

- execution ID；
- normalized columns/types/units；
- result snapshot reference；
- row count and truncation state；
- query text/hash；
- source/version/freshness；
- timing and resource usage；
- warnings/errors。

### 7.2 Deterministic Analysis Tools

MVP 提供类型化工具：

- trend comparison；
- contribution decomposition；
- price-volume-mix decomposition；
- mix-shift analysis；
- anomaly scoring；
- reconciliation；
- sensitivity check。

输入是 Execution Result Reference 和类型化参数；输出是 Computation Result 和 Provenance。MVP 不执行模型任意生成的 Python 代码。

### 7.3 Chart Intent Renderer

输入：

- `ChartIntent`
- approved result/evidence references

输出：

- 结构化 chart specification；
- artifact metadata；
- source claim/evidence refs。

Renderer 不能改变指标、重新聚合未经批准的数据或生成新的事实性结论。

---

## 8. Module 6：Evidence & Artifact Plane

### 8.1 自动捕获顺序

```text
Tool Execution
  → Execution Record
  → Observation
  → Evidence Candidate
  → Verification
  → Evidence Relation
  → Claim
  → Artifact
```

不能先创建 Claim 文本，再由客户端传入任意 `source_id` 作为证据。

### 8.2 内部端口

- `record_execution(result)`
- `record_observation(execution_id, observation)`
- `verify_observation(observation_id, rules)`
- `link_evidence(claim_id, evidence_id, relation)`
- `compose_artifacts(task_id, claim_ids)`

### 8.3 Verification Engine

验证类别：

- semantic consistency；
- time/grain/filter consistency；
- join/cardinality safety；
- aggregate/detail reconciliation；
- contribution reconciliation；
- data quality/freshness；
- evidence sufficiency；
- language/causality policy。

输出 `ValidationResult`，包含 rule ID/version、status、severity、details、inputs 和 timestamp。

### 8.4 Artifact Composer

只使用已验证 Claim/Evidence 生成：

- KPI cards；
- waterfall/contribution charts；
- investigation summary；
- limitations；
- executive report。

报告生成后再次执行 faithfulness validation，防止展示层新增无证据事实。

---

## 9. Module 7：Enterprise Data Connectivity

### 9.1 职责

- Source 注册与能力描述；
- Schema introspection；
- read-only session；
- query execution and cancellation；
- source identity/policy propagation；
- source freshness and version metadata。

### 9.2 端口

- `describe_source(source_id)`
- `introspect_schema(source_id)`
- `execute_readonly(query, execution_context)`
- `cancel_query(query_id)`
- `get_freshness(asset_id)`

MVP 实现 DuckDB Adapter。其他数据源只能通过同一端口增加，不把方言条件散布到 Analytical Intelligence 或 Evidence 模块。

---

## 10. 横向能力

### 10.1 Governance Policy Points

必须至少在以下位置执行策略：

1. Task 创建；
2. Context Compile；
3. Tool availability；
4. SQL parse/validate；
5. Source execution；
6. Evidence snapshot；
7. Artifact read/share/export；
8. Trace read。

### 10.2 Domain Events

MVP 事件至少包括：

- `AnalysisTaskCreated`
- `FollowUpAnalysisTaskCreated`
- `ClarificationRequested`
- `ClarificationReceived`
- `ContextCompiled`
- `AnalysisPlanCreated`
- `HypothesisProposed`
- `AnalysisStepStarted`
- `ToolExecutionRequested`
- `ToolExecutionCompleted`
- `ObservationRecorded`
- `ValidationCompleted`
- `HypothesisUpdated`
- `ClaimCreated`
- `ArtifactPublished`
- `AnalysisTaskCompleted`
- `AnalysisTaskPartiallyCompleted`
- `AnalysisTaskFailed`

领域事件用于状态和产品时间线；Audit Event 用于合规；OpenTelemetry span 用于工程可观测。三者可以关联同一 correlation ID，但不能混为一个存储概念。

### 10.3 Evaluation Hooks

每个阶段产生可评测快照：

- resolved intent；
- compiled context；
- plan/hypothesis graph；
- generated and executed query；
- observation/evidence；
- validation；
- claims/artifacts；
- complete trajectory summary。

---

## 11. 失败和降级矩阵

| 失败 | 归属 | 系统行为 | Task 状态 |
| --- | --- | --- | --- |
| 指标歧义 | Context/Intent | 请求最小澄清 | NEEDS_CLARIFICATION |
| 指标不覆盖请求期间 | Context/Intent | 调整期间、降级指标或部分回答；空值不得当零 | NEEDS_CLARIFICATION/PARTIAL |
| 权限不足 | Governance | 拒绝或缩小范围 | FAILED/PARTIAL |
| 无安全 Join Path | Context | 阻止步骤，尝试替代计划 | RUNNING/PARTIAL |
| 数据源暂时失败 | Connector/Runtime | 有界重试和恢复 | RUNNING/FAILED |
| SQL 语法错误 | Execution | 有界修复 | RUNNING/FAILED |
| 查询超预算 | Runtime/Governance | 取消查询，缩小计划 | RUNNING/PARTIAL |
| 数据陈旧或不完整 | Context/Verification | 警告、降级或停止 | PARTIAL |
| 对账失败 | Verification | 禁止形成完整结论 | RUNNING/PARTIAL |
| 无显著主因 | Analytical Intelligence | 输出无显著驱动因素，不强行归因 | COMPLETED/PARTIAL |
| 报告出现无证据事实 | Artifact Verification | 阻止发布并重新生成 | VERIFYING/FAILED |

---

## 12. 模块级 Definition of Done

一个模块只有满足以下条件才算达到 MVP 可集成状态：

- 输入输出使用已冻结领域对象；
- 不绕过 Context、Policy、Evidence 或 Runtime 状态；
- 正常、失败、拒绝、重试和恢复行为明确；
- 产生必要 Domain Event、Audit Event 和 Trace；
- 不依赖其他模块的内部存储表；
- 有组件级 Golden Cases 或确定性测试依据；
- 删除或替换第三方框架时，领域契约不改变。

开发任务应从这些端口和契约向内实现，而不是从 HTTP 路由、数据库表或 Prompt 文件向外反推架构。
