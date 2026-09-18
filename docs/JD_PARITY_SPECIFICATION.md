# Enterprise Data Agent v2 — JD Parity Specification

**Version**: 2.0.0
**Date**: 2026-09-18
**Goal**: 100% coverage of Enterprise Data Agent / NL2SQL / ChatBI job requirements

---

## 一、项目定义

$$
\boxed{
Enterprise\ Data\ Agent =\ LLM + Agent\ Runtime + Semantic\ Layer + RAG + Governed\ NL2SQL + Analytical\ Tools + Attribution + Governance + Evidence + Evaluation + Observability
}
$$

这不是 Chat with SQL Database，也不是 LangChain Demo，而是：
> **Enterprise-grade autonomous analytics system for Finance / Sales / Supply Chain business investigation.**

---

## 二、JD 能力映射表

| JD 能力要求 | 必须实现的模块 | 验收证据 |
|------------|--------------|---------|
| **1. 企业级 Data Agent** | 跨业务域 Agent Runtime | Finance/Sales/Supply Chain 三域 Demo |
| **2. 意图识别/任务路由/NL2SQL/归因/报告/工具调用/结果校验** | Supervisor + Router + NL2SQL + Tool Registry + Verifier | 完整 Trace 证据链 |
| **3. 问数/指标解释/异常诊断/趋势分析/经营归因/结论生成** | Analytics Tool Suite | 端到端分析案例 |
| **4. NL2SQL/指标匹配/维度识别/SQL生成/SQL修正/结果解释/查询安全** | Semantic Layer + NL2SQL Pipeline + Security | SQL 执行 + 评测 + 安全测试 |
| **5. 任务拆解/工具调用/状态管理/上下文管理/Python分析/图表生成/报告/追踪** | Durable Agent Runtime + OTel | OTel Trace 截图 |
| **6. 财务/经营管理/供应链/销售运营** | 三个 Domain Package | 跨域 Demo |
| **7. NL2SQL/指标问答/归因/报告评测集与流程** | Evaluation Harness | 500-case Suite Dashboard |
| **8. 数据源/语义层/知识库/Prompt/工具/权限/日志/评测** | Platform Modules | Repo Architecture |

---

## 三、技术架构

### 3.1 双查询通道

```
                         Query Planner
                              │
              ┌───────────────┴──────────────┐
              │                              │
      Governed Metric Query            Governed NL2SQL
              │                              │
      Known KPI / routine BI        Long-tail ad-hoc query
              │                              │
     Semantic Operators                  LLM SQL
              │                              ↓
     Deterministic SQL                 SQLGlot AST
              │                              ↓
              │                     Semantic Validation
              │                              ↓
              │                     Security Validation
              │                              ↓
              │                         EXPLAIN
              │                              ↓
              │                          Execute
              │                              ↓
              │                     Result Validation
              │                              ↓
              │                      SQL Repair Loop
              └───────────────┬──────────────┘
                              ↓
                         Observation
```

### 3.2 Agent Runtime

```text
Supervisor Agent
├── Intent Resolver
├── Semantic Resolver
├── Planner
├── Investigation Policy
├── Tool Router
├── Hypothesis Manager
├── Verifier
└── Report Synthesizer

状态持久化:
├── AnalysisTask
├── AnalysisPlan
├── ResolvedIntent
├── ContextPackage
├── Hypothesis[]
├── Observation[]
├── ToolExecution[]
├── Claim[]
├── Evidence[]
├── ValidationResult[]
├── Checkpoint
└── Budget
```

### 3.3 NL2SQL Pipeline

```
Question
↓
Resolved Business Intent
↓
Relevant Schema Retrieval
↓
Metric + Dimension Context
↓
Relevant Example SQL Retrieval
↓
Logical Query Plan
↓
LLM SQL Generation
↓
SQLGlot AST
↓
Syntax Check
↓
Table / Column Check
↓
Metric Semantic Check
↓
Join Cardinality Check
↓
RBAC / Row-level Policy
↓
Complexity / Cost Check
↓
EXPLAIN
↓
Execute
↓
Result Validation
↓
Repair if needed (max 2 attempts)
```

### 3.4 Complete Tool Suite

| Tool | 能力 |
|------|------|
| `metric_query` | KPI 查询 |
| `nl2sql_query` | 长尾 SQL |
| `metric_explain` | 指标解释 |
| `trend_analysis` | 趋势分析 |
| `period_compare` | MoM/YoY 比较 |
| `contribution_analysis` | 贡献度分析 |
| `pvm_analysis` | Price/Volume/Mix 分解 |
| `variance_analysis` | Budget/Actual 差异 |
| `anomaly_detection` | 异常检测 |
| `drilldown_analysis` | 多维钻取 |
| `python_analysis` | 沙箱统计计算 |
| `knowledge_search` | RAG 检索 |
| `chart_generate` | 图表生成 |
| `report_generate` | 报告生成 |
| `insight_watcher` | 主动监控 |

---

## 四、目录结构

```
enterprise-data-agent/
│
├── src/eiw/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── supervisor.py          # Supervisor Agent
│   │   ├── planner.py             # 分析计划器
│   │   ├── router.py              # 工具路由器
│   │   ├── hypothesis.py          # 假设管理器
│   │   ├── synthesizer.py         # 报告合成器
│   │   └── intent_resolver.py     # 意图识别
│   │
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── state.py               # 运行时状态
│   │   ├── checkpoint.py          # 检查点
│   │   ├── recovery.py            # 恢复机制
│   │   ├── budget.py              # 预算控制
│   │   └── context.py             # 上下文组装
│   │
│   ├── semantic/
│   │   ├── __init__.py
│   │   ├── package.py             # 语义包
│   │   ├── metrics.py             # 指标定义
│   │   ├── dimensions.py          # 维度定义
│   │   ├── glossary.py            # 业务术语表
│   │   ├── metadata.py            # 元数据
│   │   ├── resolver.py            # 语义解析器
│   │   └── time_semantics.py      # 时间语义
│   │
│   ├── nl2sql/
│   │   ├── __init__.py
│   │   ├── schema_linker.py       # Schema 链接
│   │   ├── schema_retriever.py    # Schema 检索
│   │   ├── example_retriever.py   # 示例 SQL 检索
│   │   ├── query_planner.py       # 查询规划
│   │   ├── generator.py           # SQL 生成
│   │   ├── parser.py              # SQL 解析
│   │   ├── semantic_validator.py  # 语义验证
│   │   ├── security_validator.py  # 安全验证
│   │   ├── optimizer.py           # SQL 优化
│   │   ├── executor.py            # 执行器
│   │   ├── result_validator.py    # 结果验证
│   │   ├── repair.py              # SQL 修复
│   │   └── evaluation.py          # NL2SQL 评测
│   │
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── retriever.py           # 知识检索
│   │   ├── indexer.py             # 知识索引
│   │   ├── examples.py            # SQL 示例管理
│   │   ├── glossary.py            # 业务术语库
│   │   └── data_dictionary.py     # 数据字典
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── trend.py               # 趋势分析
│   │   ├── anomaly.py             # 异常检测
│   │   ├── contribution.py        # 贡献分析
│   │   ├── pvm.py                 # PVM 分解
│   │   ├── variance.py            # 差异分析
│   │   ├── drilldown.py           # 钻取分析
│   │   └── period_compare.py      # 周期比较
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py            # 工具注册表
│   │   ├── base.py                # 工具基类
│   │   ├── sql_tool.py            # SQL 工具
│   │   ├── metric_tool.py         # 指标工具
│   │   ├── python_tool.py         # Python 工具
│   │   ├── knowledge_tool.py      # 知识工具
│   │   ├── chart_tool.py          # 图表工具
│   │   ├── report_tool.py         # 报告工具
│   │   └── insight_watcher.py     # 主动监控
│   │
│   ├── governance/
│   │   ├── __init__.py
│   │   ├── policy.py              # 策略引擎
│   │   ├── rbac.py                # RBAC 权限
│   │   ├── masking.py             # 数据脱敏
│   │   ├── audit.py               # 审计日志
│   │   └── security.py            # 安全检查
│   │
│   ├── evidence/
│   │   ├── __init__.py
│   │   ├── claim.py               # 声明管理
│   │   ├── provenance.py          # 数据溯源
│   │   ├── verifier.py            # 验证器
│   │   └── validator_registry.py  # 验证规则
│   │
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── tracing.py             # OpenTelemetry
│   │   ├── metrics.py             # 指标收集
│   │   ├── logging.py             # 日志
│   │   └── events.py              # 事件
│   │
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── runner.py              # 评测运行器
│   │   ├── metrics.py             # 评测指标
│   │   ├── graders.py             # 评分器
│   │   ├── regression.py          # 回归测试
│   │   └── cases/                 # 评测用例
│   │
│   ├── domain/
│   │   ├── models.py              # 领域模型
│   │   └── enums.py               # 枚举
│   │
│   ├── persistence/
│   │   ├── database.py            # 数据库
│   │   └── tables.py              # 表结构
│   │
│   ├── workspace/
│   │   ├── analysis.py            # 分析服务
│   │   ├── store.py               # 状态存储
│   │   ├── data.py                # 数据访问
│   │   └── provider.py            # 模型提供方
│   │
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── base.py                # 连接器基类
│   │   ├── duckdb.py              # DuckDB
│   │   └── postgres.py            # PostgreSQL
│   │
│   ├── app.py                     # FastAPI
│   └── web/
│       └── static/                # 前端
│
├── semantic_packages/
│   ├── finance/
│   │   ├── semantic-package.yaml
│   │   ├── metrics.yaml
│   │   ├── dimensions.yaml
│   │   ├── glossary.yaml
│   │   └── knowledge/
│   │
│   ├── sales_operations/
│   │   ├── semantic-package.yaml
│   │   ├── metrics.yaml
│   │   ├── dimensions.yaml
│   │   ├── glossary.yaml
│   │   └── knowledge/
│   │
│   └── supply_chain/
│       ├── semantic-package.yaml
│       ├── metrics.yaml
│       ├── dimensions.yaml
│       ├── glossary.yaml
│       └── knowledge/
│
├── knowledge_base/
│   ├── business_glossary/
│   ├── data_dictionary/
│   ├── sql_examples/
│   ├── analyst_playbooks/
│   └── faq/
│
├── evaluation/
│   ├── cases/
│   │   ├── intent_*.yaml
│   │   ├── nl2sql_*.yaml
│   │   ├── metric_*.yaml
│   │   ├── security_*.yaml
│   │   └── agent_*.yaml
│   ├── suites/
│   │   ├── intent_suite.yaml
│   │   ├── nl2sql_suite.yaml
│   │   ├── security_suite.yaml
│   │   └── agent_suite.yaml
│   └── results/
│
├── data/
│   ├── curated/                   # Parquet 数据
│   └── enterprise/
│       ├── finance/
│       ├── sales/
│       └── supply_chain/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── e2e/
│   └── security/
│
├── dashboards/
│   └── evaluation_dashboard.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── NL2SQL_PIPELINE.md
│   ├── SEMANTIC_LAYER.md
│   └── EVALUATION.md
│
├── scripts/
│   ├── setup.py
│   ├── generate_data.py
│   └── import_evaluation.py
│
├── pyproject.toml
├── Makefile
├── docker-compose.yml
└── README.md
```

---

## 五、评测目标

| 指标 | 目标 |
|------|------|
| Metric Resolution | ≥ 95% |
| Dimension/Time Resolution | ≥ 95% |
| SQL Syntax Valid | ≥ 99% |
| SQL Execution Success | ≥ 95% |
| Result Semantic Correctness | ≥ 90% |
| Security Policy Escape | 0% |
| Unsupported Factual Claims | < 1% |
| Simple Query P95 Latency | < 15s |
| Agent Task Completion | ≥ 90% |
| Tool Selection Accuracy | ≥ 85% |
| Recovery Rate | ≥ 80% |

---

## 六、实现优先级

### P0 (必须完成)
1. 新目录结构创建
2. NL2SQL Pipeline 完整实现
3. 增强 Semantic Layer
4. Agent Runtime 重构
5. Tool Registry
6. Governance 模块
7. OpenTelemetry 集成
8. Evaluation Harness 扩展
9. Finance 语义包
10. 文档更新

### P1 (高质量完成)
1. Knowledge Base / RAG
2. Sales Operations 语义包
3. Supply Chain 语义包
4. PostgreSQL 连接器
5. 企业数据生成
6. Insight Watcher
7. 扩展评测用例到 200+

### P2 (完整覆盖)
1. 500-case 评测套件
2. 7 个 UI 页面
3. 图表生成工具
4. 回归测试
5. 性能优化

---

## 七、验收标准

- [ ] 所有 P0 模块有完整代码实现
- [ ] NL2SQL Pipeline 端到端可运行
- [ ] Finance 域完整 Demo 可演示
- [ ] 评测用例 ≥ 100 个
- [ ] OpenTelemetry Trace 可观测
- [ ] Security 测试用例 ≥ 20 个
- [ ] README 更新为 JD Parity 版本
