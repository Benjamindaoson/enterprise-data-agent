# Enterprise Intelligence Workspace：架构与开发基线

> Subtitle: Built on Enterprise Data Agent Platform  
> Status: Architecture Baseline v0.3  
> Date: 2026-09-01  
> Scope: 产品定位、系统边界、核心领域模型、MVP 架构、技术决策与验收依据

配套设计文档：

- [核心模块设计](core-module-design.md)
- [MVP Vertical Slice 设计](mvp-vertical-slice-design.md)
- [Phase 0 实施计划](phase-0-implementation-plan.md)
- [ADR-001：MVP 主数据集与双轨评测数据策略](adr/ADR-001-primary-demo-dataset.md)
- [MVP 数据基础冻结设计](data-foundation-design.md)

## 0. 文档用途

本文档是 Enterprise Intelligence Workspace 第一阶段的开发依据。需求拆分、模块设计、接口定义、技术选型和验收应以本文档为基线。

本文档冻结的是产品目标、架构边界、核心契约和 MVP 主路径。具体模型版本、第三方托管服务以及非核心实现库，不在此阶段永久绑定。

两份前置方案的处理结论如下：

| 输入方案 | 结论 |
| --- | --- |
| “七个能力平面 + 两个横向控制面” | 作为能力架构基线 |
| 按能力平面罗列的技术栈方案 | 作为候选技术清单，不直接视为冻结选型 |

关键修正：

- 不把 SQL、Python、Visualization、Report 包装成独立 Agent，它们是受治理的工具或渲染器。
- Analytical Intelligence 决定“分析什么”；Runtime 决定“如何可靠执行”。
- 不建设万能 Memory；任务状态、企业上下文和历史分析资产分别管理。
- Evidence 是生产数据模型；Evaluation 是横向质量控制能力，二者不能合并为同一模块。
- Governance 和 Evaluation 贯穿全链路，不是流程末端的补充功能。
- 不展示模型原始思维链，只展示结构化计划、假设、工具事件、观察结果和可审计的决策摘要。
- MVP 实现 Evidence-native Analytical Agent Core，不宣称已完成通用 Enterprise Data Agent Platform。

---

## 1. 冻结后的产品定义

### 1.1 产品定位

Enterprise Intelligence Workspace 是面向企业经营分析场景的 AI 原生分析工作空间。它将业务问题转化为结构化分析计划、自主数据调查、可验证结论和决策建议。

核心产品承诺：

> 将业务问题稳定地转化为语义正确、过程可控、结果可验证的分析结论。

### 1.2 第一阶段目标用户

- 业务分析师
- 经营负责人
- 需要完成经营归因分析的数据驱动业务经理

第一阶段不同时服务数据工程、全员知识问答和企业流程自动化三类需求。

### 1.3 核心用户任务

用户提出一个经营问题，系统负责：

1. 理解指标、范围、时间和比较基线。
2. 编译与任务相关、权限允许的企业上下文。
3. 生成结构化分析计划和候选假设。
4. 在预算内查询、分解、验证并更新调查方向。
5. 为重要结论建立 Claim-Evidence 关系。
6. 输出图表、调查视图和管理摘要。
7. 支持任务重放、失败诊断和版本评测。

### 1.4 MVP 自主性边界

MVP 可以自主：

- 解析业务问题；
- 规划分析步骤；
- 生成和验证只读查询；
- 调用确定性统计工具；
- 在有限深度和预算内下钻；
- 支持、反驳或保留假设；
- 生成带证据的结论和建议。

MVP 不可以：

- 修改源数据；
- 执行 ERP、CRM 等业务写操作；
- 将推断描述为已验证事实；
- 绕过源系统或应用层权限；
- 在证据不足时强行归因；
- 依赖不可审计的自由多 Agent 对话完成主流程。

---

## 2. 冻结后的能力架构

系统采用七个能力平面和两个横向控制面。它们是协作关系，不是七个依次调用的独立服务。

### 2.1 七个能力平面

#### 1. Experience & Collaboration Plane

负责用户与分析系统协作：

- Analysis Workspace
- Investigation View
- Evidence View
- Chart/Dashboard View
- Report Workspace

#### 2. Analytical Intelligence Plane

负责业务分析决策：

- Business Understanding
- Semantic Resolution Request
- Analysis Planning
- Hypothesis Management
- Investigation Policy
- Conclusion and Recommendation Synthesis

该平面输出结构化对象，不以自由文本思维链作为运行状态。

#### 3. Enterprise Context Intelligence Plane

负责建立和编译企业上下文：

- Semantic & Metric System
- Domain Business Rules
- Schema and Catalog Metadata
- Metric Dependency and Join Relationships
- Data Quality and Freshness
- User/Role/Policy Context
- Context Compiler

Enterprise Context Graph 是逻辑关系模型；MVP 不要求图数据库。

#### 4. Agent Runtime Plane

负责可靠执行已经形成的分析计划：

- Task Lifecycle
- State Persistence
- Step Scheduling
- Tool Routing
- Budget and Stop Conditions
- Checkpoint/Resume
- Retry/Failure Handling
- Trace/Replay

Runtime 不负责重新定义业务目标，也不拥有企业知识真相。

#### 5. Governed Analysis Execution Plane

负责受约束的数据和计算执行：

- Read-only SQL Executor
- SQL Validation and Policy Checks
- Deterministic Statistical Tools
- Limited Dataframe Analysis
- Visualization Specification Renderer
- Execution Resource Limits

#### 6. Evidence & Artifact Plane

负责保存可复核的分析资产：

- Observation
- Claim
- Evidence
- Query/Computation Provenance
- Validation Result
- Chart Specification
- Report Artifact
- Historical Analysis Artifact

#### 7. Enterprise Data Connectivity Plane

负责连接已有企业数据系统：

- 数据库/数据仓库连接适配
- Schema Introspection
- Query Pushdown
- Source Identity and Permission Propagation
- Data Freshness Metadata

本项目不重建数据仓库、数据湖、BI 平台或企业 IAM。

### 2.2 两个横向控制面

#### Trust, Security & Governance

贯穿 Context、Runtime、Execution、Evidence 和 Report：

- Identity and Tenant Context
- RBAC/ABAC Policy
- Row/Column/Metric Access Policy
- Query Policy and Resource Budget
- Sensitive Data Handling
- Audit Events
- Artifact Classification and Sharing Policy

#### Evaluation & Observability

贯穿开发、测试和生产运行：

- Golden Evaluation Cases
- Domain Metrics
- Runtime Trace
- Failure Taxonomy
- Regression Comparison
- Human Review
- Cost/Latency Monitoring

### 2.3 核心闭环

```text
Business Question
        ↓
Intent and Semantic Resolution
        ↓
Permission-aware Context Compilation
        ↓
Typed Analysis Plan and Hypothesis Graph
        ↓
Durable Runtime
        ↓
Governed Execution → Observation → Evidence Capture
        ↑                              ↓
        └──── Hypothesis Update ← Verification
                                       ↓
                             Claim and Artifact Generation
                                       ↓
                           Workspace / Chart / Report
```

Governance 在每个箭头处执行；Evaluation 对每个阶段分别评分。

---

## 3. 核心领域模型

在实现页面、Prompt 或工作流之前，必须先冻结以下领域对象及其版本规则。

| 对象 | 职责 | 关键约束 |
| --- | --- | --- |
| `AnalysisTask` | 一次完整业务分析任务 | 绑定用户、领域、问题、预算和上下文版本 |
| `AnalysisContext` | 本次任务的最小充分上下文 | 权限过滤、可版本化、可重放 |
| `AnalysisPlan` | 结构化分析计划 | 包含目标、步骤、依赖、预算和停止条件 |
| `AnalysisStep` | 可调度的最小分析步骤 | 输入输出明确；可重试；副作用可控 |
| `Hypothesis` | 待验证原因 | 状态必须显式，不允许只存在于 Prompt 历史中 |
| `Observation` | 工具执行后得到的客观观察 | 与执行记录和结果快照绑定 |
| `Claim` | 对业务事实或原因的陈述 | 标记事实、推断或建议 |
| `Evidence` | 支持或反驳 Claim 的证据 | 可追溯到计算、数据和语义版本 |
| `ValidationResult` | 验证规则的结果 | 区分通过、失败、警告和不可验证 |
| `Artifact` | 图表、报告、快照等交付物 | 绑定 Task、Claim 集合和数据分类 |
| `ExecutionTrace` | 可观测执行事件 | 不保存或展示原始私有思维链 |
| `EvaluationCase` | 可重复评测用例 | 包含输入、期望语义、结果和行为约束 |

已完成任务上的深度追问创建新的子 `AnalysisTask`，通过 `parent_task_id` 和显式 `reused_evidence_ids` 关联原任务。不得原地修改已完成任务的 Context、Plan、Claim 或 Evidence；只有经过权限与版本检查的上下文和证据可以复用。

### 3.1 任务状态机

```text
CREATED
  → CONTEXT_READY
  → PLANNED
  → RUNNING
  → VERIFYING
  → COMPLETED
```

允许的非成功终态：

- `NEEDS_CLARIFICATION`
- `PARTIAL`
- `FAILED`
- `CANCELLED`

关键规则：

- 语义歧义会实质改变结果时进入 `NEEDS_CLARIFICATION`。
- 关键验证失败时不能进入 `COMPLETED`。
- 部分数据不可用但仍有受支持结论时进入 `PARTIAL`。
- 每次状态迁移必须产生审计和 Trace 事件。

### 3.2 假设状态机

```text
PROPOSED → TESTING → SUPPORTED
                   → REJECTED
                   → INCONCLUSIVE
```

`SUPPORTED` 不等于因果关系已经被证明。没有因果识别设计时，结论必须使用“主要关联因素”“贡献来源”等准确措辞。

---

## 4. Enterprise Context 契约

### 4.1 Domain Semantic Package

MVP 的领域语义包至少包含：

- Metric：定义、公式、单位、负责人、版本；
- Dimension：含义、允许值、层级；
- Grain：数据和指标粒度；
- Time Semantics：业务日期、自然月/财务月、时区；
- Entity/Relationship：实体关系及 Join Cardinality；
- Join Policy：允许的 Join Path 和去重策略；
- Business Rule：业务过滤、例外和数据排除规则；
- Source Mapping：指标到数据表/字段的映射；
- Quality/Freshness：完整性和更新时间；
- Access Policy：角色可访问的指标、维度和字段。

### 4.2 Context Compiler

输入：

- 用户身份和角色；
- 原始业务问题；
- 当前任务状态；
- 当前计划或待验证假设；
- 领域语义版本；
- 数据源可用性和新鲜度。

输出 `AnalysisContext`：

- 已解析指标和候选歧义；
- 时间、粒度、范围；
- 允许使用的维度和 Join Path；
- 相关业务规则；
- 可访问的数据源和工具；
- 数据质量告警；
- 上下文版本和来源。

Context Compiler 是核心产品模块，不是简单向量检索或 Prompt 拼接。

---

## 5. Analytical Intelligence 契约

### 5.1 Analysis Plan

计划至少包含：

- Business Objective
- Resolved Scope
- Baseline/Comparison Period
- Required Metrics
- Candidate Hypotheses
- Ordered/Conditional Steps
- Evidence Required per Step
- Query/Tool Budget
- Clarification Conditions
- Stop Conditions
- Completion Criteria

### 5.2 Investigation Policy

每轮执行后系统必须判断：

1. 当前观察支持、反驳还是不能判断某个假设？
2. 是否发现新的高价值假设？
3. 下一步是否能够显著增加证据？
4. 是否达到深度、查询数、时间或成本预算？
5. 是否已有足够证据回答核心问题？
6. 是否应降级为部分结论或请求澄清？

MVP 使用单一 Analytical Orchestrator。Planner、Investigator、Verifier 是逻辑角色，不是彼此自由对话的独立 Agent。

---

## 6. Evidence 与 Verification 契约

### 6.1 Claim 类型

- `FACT`：可直接由数据结果确认。
- `INFERENCE`：由多个观察综合推断。
- `RECOMMENDATION`：由已验证事实和业务规则产生的建议。

用户界面必须区分三类 Claim。

### 6.2 Evidence 最小字段

每条重要 Evidence 至少保存：

- 支持或反驳的 Claim ID；
- Observation ID；
- Tool/Executor 和版本；
- Query 或 Computation 标识及参数；
- Result Snapshot 或可验证摘要；
- Dataset/Source；
- Metric/Context Version；
- 执行时间与数据新鲜度；
- 用户和权限范围；
- Validation Results；
- Evidence Relation：`SUPPORTS`、`REFUTES` 或 `QUALIFIES`。

### 6.3 MVP 验证规则

- 指标公式和单位一致；
- 时间范围和比较基线一致；
- Join Cardinality 不导致重复计算；
- 汇总与分解结果可对账；
- 贡献度合计满足容差；
- 数据新鲜度达到领域要求；
- 重要 Claim 至少有一条直接 Evidence；
- 原因性措辞不得超过证据能力；
- 关键验证失败时阻止“已完成”报告。

---

## 7. MVP Vertical Slice

### 7.1 冻结场景

领域：Iowa 酒类批发经营分析（Retail Distribution Intelligence）。  
核心任务：批发销售额与批发价差的变化贡献分析。  
代表问题：

> 2026 年 7 月 Iowa 酒类批发销售额和批发价差较 6 月及去年同期发生了什么变化？哪些 Store、County、Vendor、Category 和 Product 是主要贡献来源？变化可由数量、单位批发价还是产品结构解释到什么程度？

该场景使用 Iowa Department of Revenue 的 Class E 持牌门店采购/批发订单数据。它不是消费者 POS 数据；`wholesale_gross_spread` 是州方取得成本与门店采购金额之间的批发价差，不是门店利润或完整会计利润。具体数据、许可、快照和评测分工以 ADR-001 为准。

初始不可变数据版本为 `iowa_liquor_snapshot_2026_07_v1`，覆盖 2024-01-01 至 2026-07-31；其中成本和批发价差指标仅从 2025-07-01 起可用。`iowa_liquor_rolling` 只是指向已通过验收 Snapshot 的别名，Evidence 和 Evaluation 必须绑定解析后的不可变版本。完整字段映射、快照、质量和存储契约以《MVP 数据基础冻结设计》为准。

### 7.2 领域范围

核心指标：

- Wholesale Sales Amount
- State Acquisition Cost
- Wholesale Gross Spread
- Wholesale Spread Rate
- Bottles Ordered
- Volume Liters
- Average Wholesale Price per Bottle
- Average State Cost per Bottle

核心维度：

- Order Date / Month / Year
- Store
- County / City
- Vendor
- Product / Category
- Pack / Bottle Volume

核心分析能力：

- 趋势与基线比较；
- 批发销售额/州方取得成本/批发价差分解；
- 数量、组合均价和产品 Mix 分解；
- 产品 Mix 贡献；
- County/Store/Vendor/Category/Product 下钻；
- 贡献度排序；
- 对账和敏感性检查。

MVP 采用双轨数据：固定 Iowa 官方快照用于真实展示和数值基准；小型确定性合成夹具用于权限、数据质量、Join 陷阱、无主导因素和恢复测试。生产 Demo 不以未知答案代替 Golden Ground Truth。

### 7.3 用户可见流程

1. 用户创建分析任务。
2. 系统展示已解析的指标、时间、范围和必要澄清。
3. 系统展示结构化分析计划。
4. Investigation View 按事件显示正在验证的假设、工具执行和观察结果。
5. 系统展示被支持、被反驳和无法判断的假设。
6. 最终页面展示贡献来源排序、图表、Evidence Cards、限制条件和管理摘要。
7. 用户可以查看证据详情并重放任务。

### 7.4 MVP 八个核心模块

1. Analysis Workspace
2. Domain Semantic Package
3. Context Compiler
4. Analysis Planner + Hypothesis Engine
5. Durable Task Runtime
6. Governed SQL + Deterministic Analysis Tools
7. Evidence Ledger + Verification Engine
8. Evaluation Harness

### 7.5 明确不进入 MVP

- 通用 ChatBI 平台；
- 多领域自动建模；
- DataHub/OpenMetadata 深度集成；
- Neo4j 或专用图数据库；
- 开放式多 Agent 协作；
- Temporal 分布式工作流平台；
- 任意模型生成 Python 代码并执行；
- 聚类、通用回归和完整 A/B Test 平台；
- 多数据库方言全覆盖；
- Dashboard 拖拽编辑器；
- PPT/DOCX 自动生成；
- ERP/CRM 写回和自动业务动作；
- 泛化长期记忆。

---

## 8. MVP 技术决策

状态说明：

- `FROZEN`：MVP 主路径，开发默认采用。
- `ADAPTER`：冻结抽象接口，不冻结唯一供应商。
- `DEFERRED`：不进入 MVP。

| 能力 | 决策 | 状态 | 说明 |
| --- | --- | --- | --- |
| Frontend | React + TypeScript + Vite | FROZEN | 构建分析工作空间 |
| UI | Ant Design | FROZEN | 企业应用基础组件 |
| Visualization | Apache ECharts | FROZEN | MVP 只保留一个图表库 |
| Frontend server state | React Query | FROZEN | 管理任务和结果的服务端状态 |
| Frontend local view state | Zustand | FROZEN | 仅管理工作区视图状态 |
| Backend | Python + FastAPI + Pydantic | FROZEN | API、领域契约和结构化校验 |
| Agent orchestration | LangGraph | FROZEN | 主状态图、checkpoint、条件调查循环 |
| OpenAI Agents SDK | 不进入主 Runtime | DEFERRED | 可作为后续 OpenAI-native Runtime 适配方案 |
| Distributed workflow | Temporal | DEFERRED | 出现跨服务、超长任务和规模需求后再评估 |
| Model provider | Provider Adapter | ADAPTER | MVP 部署只配置一个主模型，不并行维护多套行为 |
| Runtime state | PostgreSQL-backed persistent state | FROZEN | 任务状态和 checkpoint 的事实来源 |
| Cache/session | 默认不依赖 Redis | DEFERRED | 证明确有缓存或吞吐需求后引入 |
| Background execution | 独立应用 Worker + 持久化任务记录 | FROZEN | 队列产品不作为领域状态事实来源 |
| Progress delivery | Server-Sent Events | FROZEN | 展示长任务进度；后续可替换传输层 |
| Semantic system | 自研轻量、版本化 Domain Semantic Package | FROZEN | 直接体现核心领域能力 |
| External semantic layer | dbt/Cube adapter | DEFERRED | 平台阶段接入，不在 MVP 同时实现 |
| Catalog | Schema introspection + curated metadata | FROZEN | MVP 不部署完整数据目录产品 |
| Context graph | PostgreSQL relational/JSON representation | FROZEN | 图是逻辑模型，不引入 Neo4j |
| Demo analytical source | DuckDB + 固定 Iowa 列式快照 | FROZEN | 快照绑定 manifest/fingerprint；不以 latest 作为回归基线 |
| Business data storage | Raw/Curated Parquet | FROZEN | 大文件不进入普通 Git；DuckDB 直接读取版本化列式快照 |
| Enterprise source | Connector interface | ADAPTER | 后续增加 PostgreSQL/warehouse 适配 |
| SQL execution | Read-only executor + validation/policy pipeline | FROZEN | 禁止写查询和非授权对象 |
| Python analysis | 类型化、确定性分析工具集 | FROZEN | MVP 不执行任意生成代码 |
| Generated-code sandbox | Container/isolated job | DEFERRED | 平台阶段再实现 |
| Evidence store | PostgreSQL relational model | FROZEN | 支持 Claim-Evidence-Provenance 查询 |
| Artifact store | Storage adapter；本地开发使用文件存储 | ADAPTER | 后续切换对象存储 |
| Report | Markdown/HTML + structured chart spec | FROZEN | PDF 可后续增加；不做 PPT/DOCX |
| Domain trace | PostgreSQL execution events | FROZEN | 产品可重放和审计的事实来源 |
| Telemetry | OpenTelemetry | FROZEN | 导出后端保持可替换 |
| Trace vendor | 不绑定 LangSmith/Phoenix | ADAPTER | 不同时维护两个 Trace 平台 |
| Evaluation | 自研确定性 Evaluation Harness | FROZEN | 以语义、数值、证据和策略评测为主 |
| DeepEval/RAGAS/MLflow | 非核心扩展 | DEFERRED | 有明确评测缺口后按需引入 |
| Identity | Local development identity adapter | FROZEN | 全链路携带 User/Role/Policy Context |
| Enterprise IAM | OIDC/OAuth2 adapter | DEFERRED | 企业部署阶段接入 |

### 8.1 Runtime 选型说明

MVP 不同时使用 LangGraph、OpenAI Agents SDK 和 Temporal 控制同一条主工作流。主 Runtime 只有一个状态机和一个 checkpoint 事实来源。

应用 Worker 负责领取和执行任务；LangGraph 负责分析工作流状态；PostgreSQL 负责持久化领域状态。未来如引入 Temporal，它只能承担跨服务耐久编排，不能与 Agent 状态机产生两个互相竞争的业务状态来源。

### 8.2 模型策略

- 核心领域对象必须使用结构化输出校验。
- Prompt 不充当数据库、状态机或权限系统。
- 模型供应商通过适配接口隔离。
- MVP 只为一个主模型做完整基准和回归，不承诺多模型行为完全一致。
- 模型升级必须运行完整 Evaluation Suite。

---

## 9. Governed Execution 规则

### 9.1 SQL

- 只允许只读查询。
- 只允许 Context Package 授权的数据对象。
- 执行前检查语句类型、对象、列、Join、时间范围和资源预算。
- 设置超时、扫描/返回行数和查询次数限制。
- 查询失败可以修复，但每次修复都计入预算并记录 Trace。
- 查询结果连同 Query ID、参数、Context Version 和数据新鲜度进入 Evidence Pipeline。

### 9.2 分析工具

MVP 的 Python/统计能力以类型化工具提供，例如：

- trend comparison；
- contribution decomposition；
- mix-shift analysis；
- anomaly scoring；
- reconciliation；
- sensitivity check。

模型负责选择工具和参数，不直接生成任意 Python 后执行。

### 9.3 可视化与报告

- Analytical Intelligence 生成结构化 Chart Intent。
- Renderer 将 Chart Intent 转换为 ECharts Specification。
- 报告只引用已保存的 Claim、Evidence 和 Artifact。
- 报告生成器不得新增未在 Evidence Ledger 中出现的事实性结论。

---

## 10. Evaluation 基线

### 10.1 Golden Case 结构

每个评测用例至少包含：

- 业务问题；
- 用户/角色；
- 领域和数据版本；
- 期望指标、维度、时间和过滤条件；
- 允许或禁止的 Join/数据对象；
- 期望数值或容差；
- 必须验证的假设；
- 可接受的替代分析路径；
- 期望 Claim 和 Evidence 要求；
- 是否应澄清、拒绝或部分回答。

### 10.2 评测维度

1. Intent/Semantic Accuracy
2. Time/Filter/Grain Accuracy
3. Join and Query Correctness
4. Numeric Result Accuracy
5. Plan and Hypothesis Coverage
6. Evidence Coverage and Reproducibility
7. Verification and Abstention Correctness
8. Policy Compliance
9. Runtime Success, Cost and Latency
10. Report Faithfulness

### 10.3 MVP 不可妥协的发布门槛

- 写查询或未授权数据访问：0 次。
- 每条重要事实和推断 Claim：100% 绑定 Evidence。
- 报告中的数值：100% 可追溯到已保存结果。
- 关键验证失败：不得输出为完整成功结论。
- 同一 Context/Data Version 下：结果可重放。
- 评测报告必须能区分 Context、Planning、Tool、Verification、Runtime 和 Presentation 错误。

首版 Task Success、延迟和成本的数值目标，在基准数据集完成后通过 ADR 单独冻结，避免当前阶段使用任意百分比。

---

## 11. Security 与审计边界

- `UserContext` 必须从任务创建一直传递到 Context Compiler、Executor、Evidence 和 Artifact。
- Executor 不信任模型声明的权限，只接受 Policy 层生成的授权范围。
- 分析工具不持有源系统长期凭据。
- Trace 默认不保存完整敏感结果；必要时保存摘要、哈希或受控快照。
- Audit Log 与调试 Trace 分离：前者不可随意修改，后者用于工程诊断。
- Artifact 继承其证据所涉及数据的最高分类级别。
- Recommendation 不自动触发业务写操作。

MVP 使用本地身份适配器验证权限传播设计；企业 OIDC、SSO 和真实 RLS/CLS 集成属于平台阶段。

---

## 12. 开发阶段与退出标准

### Phase 0：Contracts and Benchmark

Phase 0 内部采用两个并行且共同验收的子阶段，不新增独立 Phase -1：

- **Phase 0A — Data Foundation**：官方快照、Raw/Curated Parquet、DuckDB、质量门槛、Manifest 和 Semantic Package；
- **Phase 0B — Contracts & Benchmark**：领域契约、状态机、Evidence、Evaluation Contract、Golden Cases 和持久化边界。

0A 与 0B 必须共同退出后才能进入 Phase 1，避免先建一套脱离领域契约的数据模型，或先写一套没有真实数据约束的领域模型。

交付：

- Iowa 酒类批发领域语义包；
- 核心领域对象 Schema；
- 状态机；
- Claim-Evidence 契约；
- `iowa_liquor_snapshot_2026_07_v1` Official Snapshot 与隔离的 Controlled Fixtures；
- 30～50 个 Golden Cases；
- 失败分类体系。

退出标准：不依赖 UI，可以清楚判断一次分析运行是否正确。

### Phase 1：Trusted Query

交付：

- Analysis Task API；
- Context Compiler；
- 结构化语义解析；
- 只读 SQL 执行和验证；
- Observation/Evidence 捕获；
- 基础 Workspace。

退出标准：核心指标查询语义正确、数值可复现、权限和查询边界有效。

### Phase 2：Autonomous Investigation

交付：

- Analysis Plan；
- Hypothesis Graph；
- 条件调查循环；
- 贡献度和 Mix 分析工具；
- 预算和停止条件；
- Checkpoint/Resume。

退出标准：代表性批发销售额/价差变化任务可以在无人指定每条查询的情况下完成受限自主贡献分析，并对不能由数据证明的原因保持克制。

### Phase 3：Evidence-native Workspace

交付：

- Investigation View；
- Evidence Cards；
- 贡献来源排序与图表；
- Report Workspace；
- Trace/Replay。

退出标准：用户可以从任意重要结论回溯到指标定义、执行和数据结果。

### Phase 4：Evaluation and Flagship Hardening

交付：

- 自动评测运行；
- 版本对比；
- 失败归类；
- 安全与边界测试；
- 演示数据和完整项目说明；
- 架构决策记录。

退出标准：每次模型、Prompt、语义或工作流变更都能运行回归评测并输出可比较结果。

Phase 4 通过即为 MVP 完成。其后的 Platform Evolution 不属于 MVP Definition of Done。

### Platform Evolution

在 MVP 验证后按实际需求演进：

1. 多数据源和企业 Catalog/Semantic Layer 适配。
2. 真实 OIDC、SSO、RLS/CLS 和租户隔离。
3. 多领域 Context Graph 和指标治理。
4. 分布式耐久工作流和水平扩展。
5. 在线评测、专家反馈和持续优化。
6. 受审批的主动监控、事件触发和业务动作。

---

## 13. 技术壁垒与投入优先级

按长期差异化排序：

1. **Enterprise Context Compiler**：把企业语义、数据、权限和任务状态编译成可执行上下文。
2. **Semantic Intelligence**：解决指标、粒度、时间、Join 和业务规则的正确性。
3. **Typed Analytical Reasoning**：以计划、假设和停止条件驱动自主调查。
4. **Evidence-native Analysis**：让 Claim、计算、数据和验证天然关联。
5. **Evaluation Flywheel**：把失败轨迹和专家修正转化为持续回归资产。
6. **Analytics-aware Durable Runtime**：提供可恢复、可预算、可重放的执行。

以下不是单独的护城河：

- Agent Framework 品牌；
- 通用 RAG；
- 基础 NL2SQL；
- 图数据库；
- 通用图表生成；
- Prompt 数量；
- Agent 数量。

核心飞轮是：

```text
Context Compilation
    → Typed Investigation
    → Governed Execution
    → Evidence and Verification
    → Evaluation and Expert Feedback
    → Better Context / Rules / Plans
```

---

## 14. 仍需通过 ADR 冻结的有限决策

以下事项不阻塞架构开发，但进入对应 Phase 前必须形成 Architecture Decision Record：

1. MVP 主模型及固定版本。
2. SQL 解析/验证实现库。
3. PostgreSQL checkpoint 和领域状态的物理表边界。
4. Artifact Storage Adapter 的生产实现。
5. OpenTelemetry 的默认开发可视化后端。
6. Evaluation Case 和运行结果的具体存储格式。

演示数据集来源、业务语义、初始时间窗口、许可原则、存储职责和双轨评测策略已经由 ADR-001 与《MVP 数据基础冻结设计》冻结。实际提取产生的 row count、timestamps、checksum、快照 fingerprint 和数据画像属于 Phase 0 可验证产物，不是待定架构选择。

任何新框架进入主路径前必须回答：

- 它解决了哪个已冻结模块的明确问题？
- 是否引入第二个状态、权限、Trace 或事实来源？
- 能否通过适配器隔离？
- 删除它是否会破坏核心领域契约？
- 它属于 MVP 必需还是平台阶段能力？

---

## 15. Definition of Done

一个 MVP 分析任务只有同时满足以下条件才算完成：

- 业务问题已完成语义解析，或已明确请求必要澄清；
- Analysis Context 已版本化并绑定权限范围；
- Analysis Plan 和 Hypothesis 状态完整；
- 请求的每个指标在当前与比较期间均满足 Metric Availability；
- 所有工具调用符合权限和预算；
- 所有重要 Claim 具有 Evidence；
- 关键验证均通过；
- 报告没有超出 Evidence 的事实性陈述；
- 任务可以从持久化状态恢复和重放；
- Trace 不暴露原始私有思维链或不必要的敏感数据；
- 对应 Golden Cases 和回归检查通过。

在这些条件达到之前，项目仍是分析 Demo，而不是可信的 Enterprise Analytical Agent。
