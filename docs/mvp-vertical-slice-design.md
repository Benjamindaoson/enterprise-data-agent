# Enterprise Intelligence Workspace：MVP Vertical Slice 设计

> Status: MVP Design Baseline v0.3  
> Date: 2026-09-01  
> Parents: [架构与开发基线](architecture-development-baseline.md) · [核心模块设计](core-module-design.md)  
> Scope: MVP 场景、运行路径、逻辑数据模型、项目边界、开发顺序与验收

下一阶段执行依据：[Phase 0 实施计划](phase-0-implementation-plan.md)  
数据决策依据：[ADR-001：MVP 主数据集与双轨评测数据策略](adr/ADR-001-primary-demo-dataset.md)
数据实施契约：[MVP 数据基础冻结设计](data-foundation-design.md)

## 0. 设计结论

MVP 不实现完整 Enterprise Data Agent Platform，而使用一个完整 Vertical Slice 证明：

> 系统能够在明确的企业语义、权限和预算下，自主完成一次可重放、可验证的经营归因分析。

前置草案中的目录、API 和数据库表只能作为讨论输入，不能原样实现。本设计做出以下修正：

- 主数据域冻结为 Iowa 酒类批发经营分析；核心结果使用 `wholesale_sales_amount` 和 `wholesale_gross_spread`，不将其误称为消费者销售或门店利润。
- 只暴露 Analysis Task Resource API，不暴露 Context、SQL、Evidence、Verification 等内部写接口。
- 补齐 Analysis Step、Observation、Claim、Evidence Relation、Validation、Checkpoint、Audit 和 Evaluation Run 等核心数据对象。
- 删除模型自报 `confidence FLOAT`；Hypothesis 由状态、证据关系和验证结果表达。
- Evaluation Skeleton 和 Golden Cases 从 Phase 0 开始，不推迟到最后。
- MVP 使用 DuckDB 读取固定 Iowa 官方快照；PostgreSQL 是控制面和证据存储，不算第二个企业分析源。
- 评测采用官方快照与小型受控夹具双轨策略；公开数据的未知业务原因不能替代确定性 Ground Truth。
- Limited Python 实现为确定性分析工具集，不是任意生成代码执行器。
- 项目先采用 Modular Monolith，不按能力平面拆微服务。

---

## 1. MVP 目标与成功定义

### 1.1 冻结领域

- 领域：Iowa 酒类批发经营分析（Retail Distribution Intelligence）
- 核心任务：批发销售额与批发价差变化贡献分析
- 用户：经营负责人或业务分析师
- 分析源：DuckDB 中的固定 Iowa 官方快照，辅以小型确定性测试夹具
- 语义源：一个版本化 Iowa Liquor Wholesale Semantic Package

### 1.2 代表问题

主 Demo：

> 2026 年 7 月 Iowa 酒类批发销售额和批发价差较 6 月及去年同期发生了什么变化？哪些 Store、County、Vendor、Category 和 Product 是主要贡献来源？变化可由数量、单位批发价还是产品结构解释到什么程度？

初始快照 `iowa_liquor_snapshot_2026_07_v1` 覆盖 2024-01-01 至 2026-07-31。Golden Case 必须绑定绝对日期和 dataset fingerprint；该版本中的“最新完整月份”固定解析为 2026 年 7 月。产品可使用 `iowa_liquor_rolling` 选择已验收的最新 Snapshot，但任务创建时必须解析并持久化具体版本。

### 1.3 成功定义

一次成功运行必须：

1. 将问题解析到正确的批发销售额/价差指标、数据代表性和比较周期；
2. 使用版本化 Context Package；
3. 生成结构化 Plan 和 Hypothesis；
4. 在查询和调查预算内完成分析；
5. 对主要分解结果完成对账；
6. 为所有重要 Claim 建立 Evidence；
7. 将事实、推断、建议和限制条件分开；
8. 生成 Investigation View、Evidence Cards、图表和管理摘要；
9. 能从持久化 checkpoint 恢复；
10. 能运行 Golden Evaluation Suite 并定位失败层级。

---

## 2. MVP 物理架构

```text
Browser
  ↕ HTTP + SSE
Web App
  ↕
FastAPI Application
  ├── Public Task API
  ├── Domain Modules
  └── Read Models
        ↕
Analysis Worker
  ├── LangGraph Runtime
  ├── Context Compiler
  ├── Analytical Intelligence
  ├── Governed Tools
  ├── Evidence/Verification
  └── Artifact Composer
        ↕
PostgreSQL              DuckDB                Artifact Storage
Task/Context/Plan       Demo analytical       Local adapter in MVP
State/Evidence/Eval     source data            
```

### 2.1 进程边界

- Web：用户体验，不包含分析业务真相。
- API：接收用户命令、提供读取模型和 SSE 事件。
- Worker：执行分析任务和 checkpoint 恢复。
- PostgreSQL：领域状态、证据、评测和审计的事实来源。
- DuckDB：唯一 MVP 分析数据源。
- Artifact Storage：图表和报告文件抽象；本地开发使用文件适配器。

MVP 不引入 Redis、Temporal、Kafka 或微服务间 RPC。出现明确吞吐或跨服务耐久需求后再通过 ADR 评估。

---

## 3. 建议项目结构

目录表达模块边界，不意味着每个目录对应独立部署单元：

```text
enterprise-data-agent/
├── apps/
│   ├── api/                    # Public API and SSE
│   ├── worker/                 # Task worker entrypoint
│   └── web/                    # React workspace
├── src/enterprise_data_agent/
│   ├── domain/                 # Core domain objects and state machines
│   ├── analytical/             # Intent, planner, hypothesis, investigation
│   ├── context/                # Semantic package and context compiler
│   ├── runtime/                # LangGraph workflow and checkpoints
│   ├── execution/              # Governed SQL and deterministic tools
│   ├── evidence/               # Observation, evidence, verification, claims
│   ├── artifacts/              # Chart intent and report composition
│   ├── connectors/             # DuckDB adapter and connector ports
│   ├── governance/             # User context, policy and audit
│   └── evaluation/             # Cases, runner, metrics, failure taxonomy
├── domains/iowa_liquor_wholesale/
│   ├── semantic/               # Metrics, dimensions, joins, rules, versions
│   └── evaluation/             # Domain-specific golden expectations
├── data/
│   ├── raw/                    # Local immutable source snapshots; not normal Git payload
│   ├── curated/                # Versioned Parquet analytical model
│   ├── manifests/              # Official snapshot source/version/fingerprint
│   └── fixtures/               # Small deterministic controlled fixtures
├── tests/
│   ├── component/
│   ├── integration/
│   └── golden/
├── docs/
│   └── adr/
└── README.md
```

冻结的是模块归属，不是每个文件名。实现过程中不得跨模块直接读取对方存储表，应通过领域端口或读取模型交互。

---

## 4. Iowa Liquor Wholesale Domain Semantic Package

### 4.1 核心指标

| Metric ID | 语义 |
| --- | --- |
| `wholesale_sales_amount` | `SUM(sales_dollars)`；门店采购订单金额/州批发销售额 |
| `state_acquisition_cost` | `SUM(ROUND(state_bottle_cost * sales_bottles, 2))` |
| `wholesale_gross_spread` | Wholesale Sales Amount - State Acquisition Cost |
| `wholesale_spread_rate` | Wholesale Gross Spread / Wholesale Sales Amount |
| `bottles_ordered` | `SUM(sales_bottles)`；门店订购瓶数 |
| `volume_liters` | `SUM(sales_liters)` |
| `avg_wholesale_price_per_bottle` | Wholesale Sales Amount / Bottles Ordered |
| `avg_state_cost_per_bottle` | State Acquisition Cost / Bottles Ordered |

最终公式、空值、币种、精度、零分母和有效交易规则必须在语义包中版本化，不能只写在 Prompt 中。`state_bottle_retail` 按官方定义是门店每瓶支付金额，不是消费者零售价；`wholesale_gross_spread` 是批发价差，不是门店利润或完整会计利润。

Metric Availability 也是语义契约：销售额、瓶数、体积和组合均价在 v1 中从 2024-01-01 可用；州方成本和批发价差从 2025-07-01 可用。跨越不可用期间的请求不得把空值当作零，必须请求调整期间或降级分析。

### 4.2 核心维度

- `order_date` / month / year
- `store`
- `county` / city
- `vendor`
- `item` / product
- `category`
- `pack` / `bottle_volume`

### 4.3 关系和约束

- 明确每张事实表的 grain；
- 明确 Store、Product 等参考表的 cardinality；
- 只允许语义包声明的 Join Path；
- 时间统一到冻结的业务时区和自然月规则；
- 金额统一币种和精度；
- 每个指标绑定 owner、version、source mapping 和 quality rule。
- 历史分析优先使用事实行内属性作为 event-time truth；当前 Store/Product 快照只能补充属性，不能静默覆盖历史值。

---

## 5. 代表性 Analysis Plan

主场景的计划模板不是固定 SQL 脚本，而是受语义和数据状态约束的分析骨架：

| Step | Objective | Required Evidence | Possible Next |
| --- | --- | --- | --- |
| S1 | 验证批发销售额/价差是否变化及幅度 | 当前期、环比和同比结果 | 未发生用户所述变化则纠正前提 |
| S2 | 将价差变化分解为批发销售额和州方取得成本 | 可对账的一级分解 | 选择主要贡献分支 |
| S3 | 分解订购瓶数、组合均价和单位成本 | 贡献度结果 | 深入数量或价格分支 |
| S4 | 分析 Product/Category Mix | Mix-shift 结果 | 深入主要产品类别 |
| S5 | 对 County/Store/Vendor/Category/Product 下钻 | 排序和贡献度 | 验证候选贡献来源 |
| S6 | 交叉验证和替代解释 | 对账、敏感性、数据质量 | 支持/反驳/保留假设 |
| S7 | 形成 Claim 和建议 | Claim-Evidence Coverage | 生成 Artifact |

计划必须允许跳过低价值步骤，并在无显著贡献因素时停止，不为满足模板而制造原因解释。

---

## 6. 端到端运行序列

### Step 1：创建任务

API 创建 `AnalysisTask`，绑定可信 `UserContext`、问题、scope hint、预算和领域版本。

### Step 2：Bootstrap Context

Context Compiler 加载用户可见的业务术语、指标候选、时间规则和权限范围。

### Step 3：Intent Resolution

- 明确“批发销售额”时解析到 `wholesale_sales_amount`；
- 用户询问“销售额”时确认其指州到 Class E 门店的批发订单，而不是消费者 POS；
- 用户询问“利润”时进入 `NEEDS_CLARIFICATION`，可以提供批发价差口径，但不得静默映射为门店利润；
- 明确当前期和比较基线；
- 形成 `ResolvedBusinessIntent`。

### Step 4：Plan and Initial Hypotheses

Planner 生成 Analysis Plan，并建立初始 Hypothesis：

- 订购瓶数变化；
- 组合批发均价变化；
- 单位州方取得成本变化；
- Product/Category Mix 变化；
- Store/County/Vendor 构成变化。

### Step 5：Plan Context

Context Compiler 为计划添加指标依赖、允许维度、Join Path、数据质量和工具约束。

### Step 6：Durable Investigation

Runtime 逐步执行：

1. 编译 Step Context；
2. 产生类型化 Tool Request；
3. 执行 Policy、SQL 和预算检查；
4. 调用 Connector/Analysis Tool；
5. 自动记录 Execution、Observation 和 Evidence Candidate；
6. 执行 Verification；
7. 更新 Hypothesis；
8. 决定下一步或停止；
9. 保存 checkpoint。

### Step 7：Synthesis and Artifact

系统基于已验证 Evidence 生成：

- contribution-source ranking；
- FACT/INFERENCE/RECOMMENDATION Claims；
- limitations and unresolved alternatives；
- waterfall/contribution chart；
- executive summary。

### Step 8：Evaluation Hooks

运行结果可以与 Golden Case 比较；生产 Demo 运行也保存可复核 Evaluation Snapshot，但不阻塞用户读取已完成结果。

---

## 7. 公共 API Surface

API 只围绕 Analysis Task 和用户协作设计：

| Method | Resource | MVP 行为 |
| --- | --- | --- |
| `POST` | `/api/v1/analysis-tasks` | 创建异步分析任务 |
| `POST` | `/api/v1/analysis-tasks/{id}/follow-ups` | 基于已完成任务创建不可变子任务，显式复用允许的 Context/Evidence |
| `GET` | `/api/v1/analysis-tasks/{id}` | 获取状态、摘要和当前步骤 |
| `POST` | `/api/v1/analysis-tasks/{id}/clarifications` | 提交澄清答案并恢复任务 |
| `POST` | `/api/v1/analysis-tasks/{id}/cancel` | 取消任务 |
| `GET` | `/api/v1/analysis-tasks/{id}/events` | SSE 进度事件 |
| `GET` | `/api/v1/analysis-tasks/{id}/plan` | 读取计划 |
| `GET` | `/api/v1/analysis-tasks/{id}/investigation` | 读取假设和调查时间线 |
| `GET` | `/api/v1/analysis-tasks/{id}/claims` | 读取结论、类型和限制 |
| `GET` | `/api/v1/analysis-tasks/{id}/evidence/{evidence_id}` | 读取证据和 provenance |
| `GET` | `/api/v1/analysis-tasks/{id}/artifacts` | 读取图表和报告 |
| `POST` | `/api/v1/analysis-tasks/{id}/feedback` | 提交用户/专家反馈 |

Context Compile、SQL Execute、Evidence Write、Verification 和 Evaluation Runner 是内部能力，不作为 MVP 用户 API。Evaluation 可以通过开发命令或 CI 任务运行。

---

## 8. 逻辑数据模型

本节冻结实体职责和关系，不冻结最终 SQL DDL。

### 8.1 Task and Runtime

| Entity | 关键内容 |
| --- | --- |
| `analysis_task` | question、trusted user ref、domain/data version、parent task ref、budget、status、timestamps |
| `task_state` | current step、remaining budget、active hypotheses、state version |
| `runtime_checkpoint` | task/state version、graph checkpoint ref、created time |
| `analysis_plan` | goal、context ref、plan version、stop/completion conditions |
| `analysis_step` | kind、dependencies、required evidence、status、retry policy |
| `hypothesis` | statement、status、required evidence、parent/child relationship |

### 8.2 Context

| Entity | 关键内容 |
| --- | --- |
| `analysis_context` | stage、immutable version/hash、source refs、policy scope、warnings |
| `semantic_asset_ref` | metric/dimension/entity ID and version |
| `context_source_ref` | catalog、schema、rule、quality、policy source and version |

完整语义资产可以在版本化领域包中维护；任务只保存本次使用的引用和必要快照。

### 8.3 Execution and Evidence

| Entity | 关键内容 |
| --- | --- |
| `execution_record` | step/tool/context、input ref、query hash、result ref、usage、status |
| `observation` | normalized fact、unit、scope、execution ref、created time |
| `validation_result` | rule/version、status、severity、input refs、details |
| `claim` | type、statement、scope、limitations、status、created by/version |
| `evidence` | observation/provenance ref、quality/freshness、validation summary |
| `claim_evidence` | claim、evidence、SUPPORTS/REFUTES/QUALIFIES relation |
| `artifact` | type、storage ref/content、claim/evidence refs、classification |

Evidence、Validation 和 Claim 必须是独立实体，不能把 Claim 文本直接保存在 Evidence 表中。

### 8.4 Trace, Audit and Evaluation

| Entity | 关键内容 |
| --- | --- |
| `domain_event` | event type、task、aggregate version、public payload ref |
| `audit_event` | actor、action、resource、policy decision、timestamp |
| `trace_ref` | correlation/span refs、redaction level、telemetry backend ref |
| `evaluation_case` | input、context/data version、expectations、tags |
| `evaluation_run` | system/model/workflow version、case set、timestamps |
| `evaluation_result` | stage、metric、score/pass、failure category、evidence refs |

### 8.5 数据规则

- Task、Plan、Context、Claim 等实体都具有稳定 ID、版本和时间戳。
- Context 和已发布 Artifact 不原地修改；新变化创建新版本。
- 对已完成分析的追问创建子 Task；不得原地重开并改写父 Task 的 Plan、Claim 或 Evidence。
- 子 Task 只复用通过当前权限、dataset/semantic version 和 classification 检查的 Context/Evidence，并保存显式引用。
- Evidence 与执行结果保持可追溯关系。
- 大结果存 Artifact/Result Storage，PostgreSQL 保存受控引用和摘要。
- 敏感原始数据不默认复制到 Trace 或 Evaluation 表。
- 状态值使用受控枚举和合法迁移，不使用任意字符串。

---

## 9. MVP Tool Set

### 9.1 SQL Pipeline

- semantic query construction；
- SQL generation；
- parse and statement validation；
- allowed asset/column check；
- join and grain validation；
- row/time/query budget；
- read-only execution；
- normalized result and provenance。

### 9.2 Deterministic Analysis Tools

- period-over-period trend；
- contribution decomposition；
- price-volume-mix；
- wholesale spread/cost decomposition；
- product/category mix shift；
- dimension ranking；
- reconciliation；
- sensitivity check。

### 9.3 初始开发预算

以下是可配置的开发默认值，不是生产 SLA：

| Budget | Default |
| --- | ---: |
| 最大调查深度 | 3 |
| 最大 SQL 执行次数 | 12 |
| 单步骤 SQL 修复次数 | 2 |
| 单查询最大返回行数 | 10,000 |
| 单任务墙钟时间 | 5 分钟 |
| 同时活跃假设数 | 6 |

预算用例必须覆盖正常停止、预算耗尽和部分结果三种路径。

---

## 10. Workspace 交付面

MVP 只实现一个组合式分析工作区，不实现通用 BI Builder。

### 10.1 Task Header

- 原始问题；
- 已解析指标/范围/比较周期；
- 状态和运行时间；
- 数据版本/新鲜度；
- 取消或回答澄清。

### 10.2 Plan and Investigation

- Analysis Plan；
- 当前步骤；
- Hypothesis Tree；
- SUPPORTED/REJECTED/INCONCLUSIVE 状态；
- 用户可见工具事件和 Observation 摘要。

### 10.3 Findings

- contribution-source ranking；
- contribution waterfall；
- trend and breakdown charts；
- FACT/INFERENCE/RECOMMENDATION 分区；
- limitations and alternative explanations。

### 10.4 Evidence View

- Claim；
- Evidence relation；
- Metric/Context Version；
- Query/Computation provenance；
- data freshness；
- validation results；
- result preview with access control。

### 10.5 Report

- Markdown/HTML executive summary；
- 使用已保存 Claim 和 Artifact；
- 不提供 PPT/DOCX；
- 生成后执行 faithfulness validation。

---

## 11. Golden Evaluation Suite

Phase 0 建立 30～50 个用例，建议首版 44 个：

| Category | Count | 示例 |
| --- | ---: | --- |
| Happy-path semantic/numeric | 10 | 正确批发销售额/价差、时间和贡献分析 |
| Ambiguity/time/grain | 8 | 消费者销售与批发订单混淆、利润口径、环比/同比 |
| Policy/authorization | 8 | 禁止 Store/County/字段、越权 Evidence |
| Data quality/no-answer | 8 | 数据陈旧、历史维度不一致、无显著主因 |
| Runtime/recovery/robustness | 10 | SQL 修复、超预算、恢复、部分完成 |

每个 Case 至少有：

- input and trusted user；
- semantic expectations；
- permitted sources/joins；
- expected numeric result or tolerance；
- required/forbidden claims；
- evidence and validation requirements；
- expected terminal status；
- failure category when not passed。

LLM Judge 只能评估难以确定性判断的表达质量。语义、权限、SQL、数值、Evidence Coverage 和状态迁移优先使用确定性评测。

---

## 12. 开发顺序

开发按价值闭环推进，不按七个平面分别做完。

### Phase 0：Contracts and Benchmark

Phase 0 包含共同验收的 0A Data Foundation 与 0B Contracts & Benchmark，不新增独立 Phase -1。

先完成：

1. v1 Official Snapshot、Raw/Curated Parquet、DuckDB Views 和数据质量门槛；
2. Iowa 酒类批发指标、Metric Availability、数据代表性和时间规则；
3. 领域对象和状态机；
4. Snapshot manifest/fingerprint 与隔离的受控测试夹具；
5. 44 个 Golden Case 结构和首批关键用例；
6. Evidence/Validation 契约；
7. 模块端口、ADR 和最小工程骨架。

退出标准：无需完整 UI 和 Agent，即可人工或确定性计算 Golden Case 的正确结果。

### Phase 1：Trusted Query Walking Skeleton

建立最薄的端到端链路：

```text
Task → Bootstrap Context → Fixed/Minimal Plan → Governed SQL
     → Observation → Evidence → Verified Claim → Minimal Report
```

此阶段重点是语义、权限、数值和 Evidence，不追求自主调查深度。

### Phase 2：Autonomous Investigation

加入：

- 动态 Plan；
- Hypothesis Lifecycle；
- contribution/mix 工具；
- Investigation Decision；
- budgets and stop conditions；
- checkpoint/resume。

### Phase 3：Evidence-native Workspace

加入：

- SSE progress；
- Plan/Investigation View；
- Evidence Cards；
- Chart Intent/Renderer；
- executive report；
- feedback capture。

### Phase 4：Evaluation and Flagship Hardening

加入：

- 完整 Golden Suite；
- regression comparison；
- failure taxonomy dashboard/report；
- policy and recovery tests；
- demo scripts and architecture documentation；
- release acceptance report。

Phase 4 通过即视为 MVP 完成。多数据源、多领域、企业 IAM、多租户、在线 Evaluation 和分布式 Runtime 属于 Post-MVP Platformization，不计入 MVP 完成条件。

---

## 13. Demo 场景矩阵

旗舰演示不能只有单一路径：

| Demo | 证明能力 | 期望行为 |
| --- | --- | --- |
| v1 最新完整月份经营调查 | 完整自主调查 | 将“最新”解析为 2026 年 7 月，输出环比/同比贡献、Evidence、图表和报告 |
| 对 Vendor X 继续追问 | Context Continuity | 创建子 Task，复用允许的证据并继续 Product/Store/Mix 下钻 |
| 用户询问“门店利润为何下降” | 语义治理 | 说明数据边界并请求澄清，不能伪造利润口径 |
| 受限用户请求 Store 明细 | 权限传播 | 拒绝该维度或降级到 County/Category |
| 官方快照陈旧或维度映射异常 | 数据质量 | 明确警告并输出 PARTIAL |
| 多因素小幅变化、无主导因素 | 正确克制 | 不强行给出单一根因或因果结论 |
| 中途执行失败后恢复 | Durable Runtime | 从 checkpoint 继续且不重复 Evidence |

旗舰演示采用一个连续故事：

```text
选择 v1 Official Snapshot
  → “最新完整月份”解析为 2026-07
  → 自主计划和多维贡献调查
  → 图表、Claims、Evidence 和 Executive Report
  → 对 Vendor X 发起 follow-up child task
  → 复用允许的 Evidence 继续 Product/Store/Mix 下钻
  → 询问门店净利润
  → 系统说明数据边界并正确拒绝错误归因
  → 展示对应 Golden/Evaluation Result 与 Trace/Replay
```

Workspace 的 Dynamic BI 仅指根据结构化 Chart Intent 生成受控图表和调查视图，不包含拖拽 Dashboard Builder。

---

## 14. MVP 验收

### 14.1 产品验收

- 用户可以创建、跟踪、澄清和取消任务；
- 用户可以看到 Plan、Investigation、Evidence 和 Report；
- 所有用户可见结论区分 FACT/INFERENCE/RECOMMENDATION；
- 无证据或关键验证失败的 Claim 不会发布。

### 14.2 分析验收

- `wholesale_sales_amount`、`wholesale_gross_spread`、时间和比较基线解析正确；
- 每个请求指标在当前期与比较期均通过 Metric Availability 检查；
- 不把批发订单表述为消费者 POS，也不把批发价差表述为门店利润；
- 主场景一级和二级分解可对账；
- 无显著主导贡献因素时正确停止；
- 不将贡献关系表述为已证明因果。

### 14.3 Runtime 验收

- 状态迁移合法；
- checkpoint 可恢复；
- retry 和 SQL repair 有界；
- 预算耗尽产生 PARTIAL，而不是无限循环；
- 重放不重复写 Observation/Evidence。

### 14.4 Trust 验收

- 写查询和越权访问为 0；
- 每个重要 Claim 100% 绑定 Evidence；
- 每个报告数值可追溯；
- Audit、Domain Event 和 Trace 可关联但相互区分；
- Trace 不包含不必要的敏感数据或模型原始思维链。

### 14.5 Engineering 验收

- 领域模块不依赖 Web/UI；
- 内部模块不通过自调用 HTTP 协作；
- Connector、Model、Artifact、Telemetry 使用适配器边界；
- 每个关键阶段有组件或 Golden Case 验证；
- 技术框架替换不改变核心领域契约。

---

## 15. 进入开发前仍需完成的 ADR

1. 主模型和固定版本。
2. SQL parser/validator。
3. LangGraph PostgreSQL checkpoint 与领域状态的边界。
4. Domain Semantic Package 的物理格式。
5. OpenTelemetry 开发后端。
6. Artifact 本地存储路径和生命周期。

Demo 数据域、许可原则、快照窗口、字段映射、指标可用期、存储职责和双轨评测策略已由 ADR-001 与《MVP 数据基础冻结设计》冻结。实际提取产生的 row count、timestamps、fingerprint 和数据画像是 Phase 0 Gate C 的可验证产物。

这些决策完成后，从 Phase 0 开始实现。未经 ADR，不得将新的 Agent Framework、图数据库、Catalog 平台或任意代码执行环境加入 MVP 主路径。
