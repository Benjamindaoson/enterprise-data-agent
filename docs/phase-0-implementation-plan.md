# Enterprise Intelligence Workspace：Phase 0 实施计划

> Status: Ready with Entry Gates v0.3  
> Date: 2026-09-01  
> Parents: [架构与开发基线](architecture-development-baseline.md) · [核心模块设计](core-module-design.md) · [MVP Vertical Slice 设计](mvp-vertical-slice-design.md)  
> Scope: Contracts and Benchmark；本阶段不实现完整 Agent、UI、Dashboard 或 Report

数据决策依据：[ADR-001：MVP 主数据集与双轨评测数据策略](adr/ADR-001-primary-demo-dataset.md)
数据实施契约：[MVP 数据基础冻结设计](data-foundation-design.md)

## 0. 最终架构检查结论

架构可以进入开发阶段，不需要再次重构七个能力平面、核心领域模型或 MVP 边界。

但“创建 Pydantic Model + PostgreSQL Table + API Schema”不能被理解为同一组类直接复用。Phase 0 必须保持三类契约分离：

1. **Domain Contract**：表达业务不变量、状态机和领域关系，不依赖 FastAPI 或数据库。
2. **API Contract**：表达外部命令和读取模型，只暴露 Analysis Task Resource。
3. **Persistence Mapping**：表达 PostgreSQL 存储、索引、并发和迁移，不反向定义领域模型。

最终判断：

> 架构已冻结；Phase 0 可以开始，但必须先通过 Entry Gates，并按“源/领域契约 ↔ 数据快照 → 确定性基准 → 持久化/API 契约 → 工程验证”的闭环开发。

Phase 0 由共同验收的 **0A Data Foundation** 与 **0B Contracts & Benchmark** 构成。数据 Schema、Semantic Contract 和 Golden Expectations 必须迭代校验，因此不新增一个与 Contracts 隔离的 Phase -1。

---

## 1. Phase 0 目标

Phase 0 的目标不是让 Agent 回答问题，而是建立一个可以判断系统未来是否正确的开发地基。

交付结果必须回答：

- 什么是合法的 Analysis Task、Plan、Hypothesis、Claim 和 Evidence？
- Iowa 批发销售额、州方取得成本和批发价差如何精确定义？
- Official Snapshot 中的确定性数值和贡献结果是什么？
- 哪些故障与边界必须由 Controlled Fixture 提供已知 Ground Truth？
- 哪些问题应回答、澄清、拒绝或部分完成？
- 如何区分 Context、Planning、Query、Numeric、Evidence 和 Runtime 错误？
- 领域对象如何版本化、持久化和向外暴露，而不互相耦合？

Phase 0 不需要调用真实 LLM，也不需要生成任意 SQL。

---

## 2. Entry Gates：开始编码前必须冻结

### Gate A：开发工具链 ADR

冻结：

- Python 和 Node 的支持版本；
- Python/Node 包管理方式；
- 单元测试、类型检查和格式化工具；
- PostgreSQL migration 工具；
- 本地开发启动方式；
- CI 的最小验证命令。

本 ADR 只决定工程一致性，不改变产品架构。

### Gate B：Domain Semantic Package 格式 ADR

冻结：

- 文件还是数据库作为 authoring source；
- schema/version 格式；
- metric、dimension、join、rule、policy 的目录和引用方式；
- 版本升级和兼容规则；
- 校验和/内容哈希；
- owner、currency、timezone、precision 等必填字段。

建议 MVP 使用版本控制中的声明式文件作为 authoring source，运行时加载为已校验的领域对象。具体文件格式通过 ADR 决定。

### Gate C：Demo Dataset ADR

ADR-001 与《MVP 数据基础冻结设计》已经冻结 Iowa 官方数据、字段语义、初始快照、存储职责和 Official Snapshot + Controlled Fixture 双轨策略。Gate C 的职责是生成并验收真实 manifest：

- 验证官方 catalog/table identity 和实际使用的官方提取 endpoint；
- 每个资产的 CC BY 许可、归属文本和 NOTICE 规则；
- `iowa_liquor_snapshot_2026_07_v1` 的 2024-01-01 至 2026-07-31 窗口及最大业务日期；
- `OPERATING_TREND_WINDOW` 与 `COST_SPREAD_WINDOW` 的 Metric Availability；
- `invoice_id` 唯一性、Raw/Curated Schema 和当前参考表 Join Coverage；
- 真实 row count、timestamps、schema/content fingerprint；
- 独立参考计算及其数值 Ground Truth、reference query hash 和 analyst approval metadata；
- Controlled Fixture 的固定 seed、缺陷注入和预期行为；
- 大文件的本地获取、缓存、GitHub 分发和校验方式。

Gate C 不再选择数据域或重新设计星型模型，而是把冻结契约落实为可复现资产。实际 endpoint、row count、timestamps 和 checksum 是执行后产生的 manifest 值，不是架构留白。

### Gate D：Domain/Persistence Boundary ADR

冻结：

- Domain Object 与 Persistence Record 的映射规则；
- 哪些对象不可变、哪些对象保存 current state；
- optimistic concurrency/version 字段；
- PostgreSQL checkpoint 与领域状态的职责边界；
- Result Snapshot 和大对象只保存引用还是内联；
- sensitive payload 的保存和脱敏规则。

### Gate E：Evaluation Case Contract ADR

冻结：

- Case authoring 格式；
- expectation、tolerance、tags 和 failure category；
- dataset/context version binding；
- Evaluation Run/Result 的存储方式；
- 确定性 scorer 和未来 LLM judge 的边界。

### 不阻塞 Phase 0 的 ADR

以下决策可在 Phase 1 前完成：

- 主模型及固定版本；
- SQL parser/validator；
- OpenTelemetry 默认可视化后端；
- Artifact Storage 的生产实现。

---

## 3. Phase 0 领域契约

前置 Prompt 中列出的十个对象不够。Phase 0 至少需要以下契约。

### 3.1 Identity、Task 与状态

- `UserContext`
- `AnalysisTask`
- `TaskLineage`（parent task、reused claim/evidence refs、inheritance audit）
- `TaskScopeHint`
- `TaskBudget`
- `TaskState`
- `ClarificationRequest`
- `ClarificationResponse`
- `RuntimeCheckpointRef`

### 3.2 Intent、Context 与 Plan

- `ResolvedBusinessIntent`
- `AnalysisContext`
- `ContextSourceRef`
- `SemanticAssetRef`
- `AnalysisPlan`
- `AnalysisStep`
- `Hypothesis`
- `InvestigationDecision`

### 3.3 Execution、Evidence 与 Artifact

- `ToolExecutionRequest`
- `ExecutionRecord`
- `Observation`
- `ValidationResult`
- `Claim`
- `Evidence`
- `ClaimEvidenceLink`
- `Artifact`

### 3.4 Events 与 Evaluation

- `DomainEvent`
- `AuditEvent`
- `TraceRef`
- `EvaluationCase`
- `EvaluationRun`
- `EvaluationResult`
- `FailureCategory`

### 3.5 必须冻结的枚举和状态迁移

- Task Status：`CREATED`、`NEEDS_CLARIFICATION`、`CONTEXT_READY`、`PLANNED`、`RUNNING`、`VERIFYING`、`COMPLETED`、`PARTIAL`、`FAILED`、`CANCELLED`。
- Hypothesis Status：`PROPOSED`、`TESTING`、`SUPPORTED`、`REJECTED`、`INCONCLUSIVE`。
- Claim Type：`FACT`、`INFERENCE`、`RECOMMENDATION`。
- Evidence Relation：`SUPPORTS`、`REFUTES`、`QUALIFIES`。
- Validation Status：`PASSED`、`FAILED`、`WARNING`、`NOT_VERIFIABLE`。
- Investigation Decision：`EXECUTE_STEP`、`REFINE_PLAN`、`REQUEST_CLARIFICATION`、`SYNTHESIZE`、`COMPLETE_PARTIAL`、`STOP_FAILED`。

### 3.6 通用契约规则

- 所有 ID 采用稳定、不可复用的标识。
- 所有时间使用带时区时间；业务日期与系统时间分开。
- 金额和比例使用明确精度，不使用二进制浮点表达货币。
- 所有版本化对象包含 version 和内容 fingerprint。
- 领域模型不得导入 Web、ORM、LangGraph 或特定 LLM SDK 类型。
- 状态改变只能通过合法领域操作，不允许任意字符串赋值。
- `confidence` 不能由模型自行给出；可信程度由 Evidence 和 Validation 派生。

---

## 4. API Contract 范围

Phase 0 只定义 schema，不要求实现完整业务端点。

### 4.1 Command Schemas

- Create Analysis Task
- Create Follow-up Analysis Task
- Submit Clarification
- Cancel Analysis Task
- Submit Feedback

### 4.2 Read Schemas

- Analysis Task Summary
- Analysis Plan View
- Investigation Timeline
- Claim View
- Evidence View
- Artifact View
- User-visible Event

### 4.3 API 约束

- 客户端不能提交 trusted role、policy result、Evidence 或 Validation Result。
- API 不暴露 Context Compile、SQL Execute、Tool Select、Evidence Write 或 Verification Run。
- API Schema 可以引用 Domain Value Object，但不能直接返回 Persistence Record。
- 错误响应必须区分 validation、clarification、policy denial、not found 和 conflict。

---

## 5. PostgreSQL 初始持久化范围

Phase 0 冻结逻辑关系并创建初始 migration；最终物理表细节由 Gate D ADR 约束。

### 5.1 Task and Runtime

- `analysis_task`
- `task_state`
- `runtime_checkpoint`
- `analysis_plan`
- `analysis_step`
- `hypothesis`

### 5.2 Context

- `analysis_context`
- `context_source_ref`
- `semantic_asset_ref`

### 5.3 Execution and Trust

- `execution_record`
- `observation`
- `validation_result`
- `claim`
- `evidence`
- `claim_evidence`
- `artifact`

### 5.4 Events and Evaluation

- `domain_event`
- `audit_event`
- `evaluation_case`
- `evaluation_run`
- `evaluation_result`

### 5.5 存储原则

- `analysis_task` 和 `task_state` 保存 current state，并使用并发版本。
- Context、Plan Version、Checkpoint、Execution、Observation、Validation、Claim、Evidence、Event 和 Evaluation Result 采用 append/versioned 模式。
- `claim` 与 `evidence` 分表，通过 `claim_evidence` 表达多对多和关系类型。
- 大查询结果和 Artifact 不直接无限写入 JSONB；保存受控 snapshot reference、摘要和 fingerprint。
- Audit 与 Trace 分离，Trace 只保存外部 telemetry reference 和必要脱敏元数据。
- 每张表的 tenant/user/classification 字段由 Gate D 明确，不能上线后补安全边界。

---

## 6. Demo Dataset 设计

### 6.1 Official Snapshot Track

主事实源：`Iowa Liquor Sales, January 2012 - Current` 的固定时间窗口。

MVP 快照窗口：

- Dataset Version：`iowa_liquor_snapshot_2026_07_v1`；
- 业务日期：2024-01-01 至 2026-07-31；
- 主比较：2026 年 7 月 vs 2026 年 6 月；
- 第二比较：2026 年 7 月 vs 2025 年 7 月；
- 实际实现时验证官方源的最大业务日期和 last-updated timestamp。

逻辑表：

- `fact_liquor_order_line`：每个官方 `invoice_id` 一行；将 `sales_bottles` 规范为 `bottles_ordered`，并保留交易时的 Store/County/Vendor/Category/Product 属性；
- `ref_liquor_store_current`：可选的当前门店参考快照；
- `ref_liquor_product_current`：可选的当前产品参考快照；
- `dim_date`：本项目确定性生成的日期维度。

历史分析以事实行内属性作为 event-time truth。Store/Product 当前表只有在唯一性和缺失率验证通过后才能补充当前属性，不能覆盖事实行的历史属性。

官方 Schema 标注 `state_bottle_cost` 和 `state_bottle_retail` 在 2025-07-01 前不可用。销售额/瓶数/体积可以覆盖 v1 全窗口；州方成本和批发价差只允许用于所有比较期间均不早于 2025-07-01 的任务。空值不得当作零。

### 6.2 Official Snapshot Ground Truth

公开数据中的业务变化不由项目预先注入，但快照冻结后必须建立独立参考答案：

- 2026 年 7 月与环比/同比的指标总量和差额；
- Wholesale Sales Amount、State Acquisition Cost 和 Wholesale Gross Spread 恒等式；
- County/Store/Vendor/Category/Product 贡献排序；
- Bottles、组合均价和 Product Mix 分解；
- 汇总与分解的 reconciliation tolerance；
- 不得发布的因果性或消费者销售 Claim。

Agent 可以在运行时不知道答案；Evaluation Harness 必须知道数值答案、容差和允许的替代分析路径。

Ground Truth 只有在绑定 Snapshot/Semantic fingerprint、reference computation hash，并记录 `reviewed_by`、`reviewed_at`、`review_status=APPROVED` 后才能进入 Golden Suite。

### 6.3 Controlled Fixture Track

至少提供以下小型、确定性场景：

- stale official snapshot metadata；
- missing Store/Product mapping；
- current-dimension duplicate join trap；
- no-dominant-driver period；
- restricted Store/County detail；
- unsupported consumer-demand or retailer-profit question；
- checkpoint/retry/idempotency fixture。

这些场景不是随机脏数据，也不用于替换 Iowa 产品故事；它们用于稳定验证公开数据无法保证出现的失败路径。

### 6.4 数据可复现性与许可

- Official Snapshot 保存 source、query、时间范围、row count、schema/content fingerprint 和最大业务日期；
- Controlled Fixture 固定 seed、生成配置和 Ground Truth；
- 固定业务时区、币种和 decimal precision；
- 输出 schema、数据画像和行数摘要；
- Golden Case 绑定 fingerprint，不只绑定文件名或 `latest`；
- 保存逐资产 CC BY 信息、Iowa Department of Revenue 归属和修改说明；
- 大型官方数据默认不直接提交 Git，使用受校验的本地/Release 获取流程。
- Raw/Curated 业务数据使用 Parquet，DuckDB 查询；PostgreSQL 只保存 Agent 状态、Evidence 和 Evaluation。

---

## 7. 第一批 Golden Cases

第一批开发实现 12 个 Case；Phase 0 完成前扩展到计划中的 30～50 个，目标基线为 44 个。

| ID | Category | Input | Expected Core Behavior |
| --- | --- | --- | --- |
| GC-001 | Semantic/Numeric | 2026 年 7 月 Iowa 批发销售额较 6 月变化 | 解析 `wholesale_sales_amount`，给出快照中的正确差额 |
| GC-002 | Decomposition | 批发价差变化来自销售额还是州方成本 | 一级分解可对账 |
| GC-003 | Product Mix | 哪些 Category/Product 贡献最大 | 给出确定性贡献排序和 Evidence |
| GC-004 | Price/Volume/Mix | 变化来自瓶数、组合均价还是 Mix | 分解可对账并标记剩余项 |
| GC-005 | Store/County | 哪些 Store/County 贡献最大 | 正确排序并遵守粒度与权限 |
| GC-006 | Semantic Boundary | 为什么门店利润下降 | 不映射为批发价差；说明数据边界并澄清 |
| GC-007 | Time Semantics | 2026 年 7 月同比发生了什么 | 正确使用 2025 年 7 月基线 |
| GC-008 | Policy | 受限用户请求 Store 明细 | 拒绝该维度或降级到允许范围 |
| GC-009 | Data Quality | 官方快照陈旧或参考维度重复 | 输出 Warning/PARTIAL，禁止重复聚合 |
| GC-010 | Abstention | 哪项营销活动导致销量变化 | 拒绝无证据因果解释，只报告可验证贡献 |
| GC-011 | Metric Coverage | 分析 2024 年批发价差 | 不把缺失成本当零；请求调整期间或降级指标 |
| GC-012 | Follow-up | Vendor X 为什么贡献大 | 创建子 Task，按权限复用父任务 Evidence 并继续下钻 |

每个 Case 必须包含：

- trusted user/role；
- dataset/context fingerprint；
- expected metric/time/scope/grain；
- allowed/forbidden assets and joins；
- expected numeric result or tolerance；
- required/forbidden claims；
- evidence and validation requirements；
- expected terminal status；
- failure category。

---

## 8. Failure Taxonomy

Phase 0 冻结下列一级分类：

| Code | 含义 |
| --- | --- |
| `INTENT_ERROR` | 目标或任务类型错误 |
| `SEMANTIC_ERROR` | 指标、维度或业务术语错误 |
| `TIME_SCOPE_ERROR` | 时间、范围或比较基线错误 |
| `GRAIN_ERROR` | 粒度不一致 |
| `JOIN_ERROR` | Join Path 或 cardinality 错误 |
| `POLICY_ERROR` | 权限或治理违规 |
| `DATA_QUALITY_ERROR` | 新鲜度、完整性或映射问题 |
| `PLANNING_ERROR` | Plan/Hypothesis 不完整或不合理 |
| `TOOL_ERROR` | 工具选择、参数或执行失败 |
| `QUERY_ERROR` | SQL 语法或执行错误 |
| `NUMERIC_ERROR` | 数值、单位或精度错误 |
| `VERIFICATION_ERROR` | 对账或验证失败未被正确处理 |
| `EVIDENCE_ERROR` | Claim-Evidence 缺失或错误 |
| `RUNTIME_ERROR` | 状态、恢复、重试或预算错误 |
| `PRESENTATION_ERROR` | 报告不忠实或展示错误 |

允许二级错误码扩展，但一级分类变更需要 ADR。

---

## 9. Phase 0 工作包

### WP0-A：ADR 和工程骨架

交付：

- Entry Gate ADR；
- 项目目录；
- 包和应用边界；
- 最小 CI；
- migration 和测试骨架。

### WP0-B：Domain Contracts

交付：

- 领域模型和值对象；
- enums；
- Task/Hypothesis 状态机；
- invariant validation；
- serialization contract。

### WP0-C：Iowa Liquor Wholesale Semantic Package

交付：

- 8 个核心指标；
- Order Date、Store、County/City、Vendor、Product/Category、Pack/Bottle Volume 维度组；
- grain、time、join 和 business rules；
- source mappings；
- package validation and fingerprint。

### WP0-D：Dataset Snapshot and Controlled Fixtures

交付：

- Iowa Official Snapshot extraction manifest；
- Dataset Lifecycle：`DISCOVERED → INGESTING → RAW_CAPTURED → PROFILING → CURATING → VALIDATING → BENCHMARKING → READY`，失败进入 `REJECTED`；
- Raw/Curated Parquet 与 DuckDB analytical views；
- deterministic reference-result manifest；
- controlled data-quality/policy/runtime fixtures；
- CC BY attribution/NOTICE metadata；
- fingerprint report。

### WP0-E：Evaluation Foundation

交付：

- Evaluation Case Contract；
- initial 12 Golden Cases；
- case loader/validator；
- deterministic expectations；
- failure taxonomy。

### WP0-F：Persistence and Migration

交付：

- persistence records/mappings；
- initial migration；
- repository ports and initial adapters；
- concurrency/version strategy；
- migration verification。

### WP0-G：API Contracts

交付：

- public command/read schemas；
- error schema；
- OpenAPI contract snapshot；
- proof that internal modules are not exposed as public write APIs。

---

## 10. Phase 0 验证要求

### 10.1 Domain Tests

- 合法和非法 Task 状态迁移；
- 合法和非法 Hypothesis 状态迁移；
- immutable/versioned object 行为；
- completed parent Task 与 follow-up child Task 的不可变关联和 Evidence reuse 约束；
- money/percentage precision；
- evidence relation 和 Claim type 约束；
- 结构化序列化 round trip。

### 10.2 Semantic Tests

- 指标公式依赖无环或显式允许；
- source mapping 完整；
- grain、unit、currency、timezone 完整；
- Join Path/cardinality 有效；
- package fingerprint 稳定；
- `retail` 字段名不被误解为消费者零售价；
- `sales` 不被误解为消费者 POS；
- 未定义的 `profit` 不静默映射到 `wholesale_gross_spread`。
- 2025-07-01 前的 Cost/Spread 请求触发 Metric Coverage 行为，空值不映射为零。

### 10.3 Dataset Tests

- Raw/Curated schema、`invoice_id` 唯一性和 grain；
- Current Store/Product Join 以 coverage/reconciliation 验证，不以删除历史事实的强 FK 验收；
- Official Snapshot 提取 manifest 和 fingerprint 可复核；
- Controlled Fixture 固定 seed 可复现；
- 指标恒等式可对账；
- 官方快照参考结果和受控夹具满足各自 Ground Truth；
- stale/missing/duplicate fixtures 可检测；
- 负值被保留为 signed adjustment 并产生必要解释告警，不被静默删除或称为退款；
- fingerprint 与 manifest 匹配。

### 10.4 Evaluation Tests

- 12 个初始 Case 可以加载并通过 schema validation；
- 每个 Case 绑定 dataset/context version；
- expectation 和 tolerance 完整；
- failure category 合法；
- 确定性参考计算可以生成预期结果。

### 10.5 Persistence Tests

- migration 可在空库应用；
- migration 可以验证回滚策略；
- FK/unique/check constraints 有效；
- optimistic concurrency 有效；
- append/versioned records 不被原地覆盖；
- Domain 与 Persistence mapping round trip。

---

## 11. Phase 0 明确不做

- LLM prompt tuning；
- LangGraph Investigation Loop；
- SQL generation/repair；
- 任意 Python 执行；
- React Workspace；
- SSE progress；
- Dashboard/Chart Renderer；
- Report Composer；
- 多 Agent；
- Memory System；
- 企业 IAM；
- 多数据源连接器；
- 在线 Evaluation Dashboard。

允许建立空的 application entrypoint 和模块骨架，但不实现上述产品能力。

---

## 12. Phase 0 Exit Criteria

只有全部满足以下条件才能进入 Phase 1：

- Entry Gate ADR 已接受；
- 核心领域契约及状态机有自动验证；
- Iowa Liquor Wholesale Semantic Package 可加载、校验和 fingerprint；
- Official Snapshot 可按 manifest 重建/校验，Controlled Fixture 可确定性生成，并分别通过 Ground Truth 检查；
- 12 个初始 Golden Case 可加载和确定性计算；
- Phase 0 结束计划已明确如何扩展到 30～50 个 Case；
- PostgreSQL 初始 migration 和 Domain Mapping 验证通过；
- API contract 不暴露内部 Tool/Evidence/Verification 写入口；
- README 能说明如何验证 Phase 0 产物；
- 没有引入新的 Agent Framework、图数据库、任意代码执行或未冻结平台能力。

---

## 13. 修正后的第一条开发任务说明

以下任务说明可以作为下一次明确授权开始开发时的输入：

```markdown
你负责实现 Enterprise Intelligence Workspace MVP 的 Phase 0：Contracts and Benchmark。

必须遵守：
- docs/architecture-development-baseline.md
- docs/core-module-design.md
- docs/mvp-vertical-slice-design.md
- docs/phase-0-implementation-plan.md
- docs/adr/ADR-001-primary-demo-dataset.md
- docs/data-foundation-design.md

不要重新设计架构，不要增加新的 Agent Framework 或未冻结能力。

开始实现前：
1. 读取全部基线文档和仓库指令。
2. 完成 Phase 0 Entry Gates 对应的 ADR；如已有明确仓库约束则遵循。
3. 将工作拆成 WP0-A 至 WP0-G，并保持 Domain、API、Persistence 三类契约分离。

本阶段实现：
1. Modular Monolith 工程骨架和最小 CI/测试/migration 能力。
2. Phase 0 文档列出的完整领域对象、枚举、不变量和状态机。
3. PostgreSQL persistence mapping 和初始 migration。
4. Iowa Liquor Wholesale Domain Semantic Package：8 个核心指标、Store/County/Vendor/Category/Product 等维度，以及 grain/time/join/rule/source/version/fingerprint。
5. Iowa Official Snapshot 的提取规范与 ground-truth manifest，以及可复现的 Controlled Fixtures。
6. Evaluation Case Contract、Failure Taxonomy 和 12 个初始 Golden Cases。
7. 面向 Analysis Task 的 API schemas；不要暴露内部 Context/Tool/Evidence/Verification 写接口。
8. 对领域、语义、数据、评测和 migration 的自动验证。

本阶段不要实现：
- UI、SSE、Dashboard、Report
- LangGraph Investigation Loop
- SQL Agent/SQL generation
- 任意 Python 执行
- Multi-Agent、Memory System
- 企业 IAM、多数据源和在线评测平台

完成标准：
- 运行 Phase 0 的全部验证；
- 报告通过项、未完成项和 ADR；
- 不以页面能运行代替领域和评测正确性。
```

此任务必须由用户明确授权“开始 Phase 0 实现”后执行。本轮最终架构检查不包含业务代码实现。
