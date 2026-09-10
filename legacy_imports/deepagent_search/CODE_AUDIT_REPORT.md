# 数据分析 Agent 项目全面技术审计报告

审计日期：2026-07-07
审计范围：`main.py`、`api/`、`agent/`、`tools/`、`prompt/`、`sql/`、`evals/`、`pyproject.toml`、环境配置示例和可运行检查。
说明：本报告区分“已验证事实”“基于代码推断的风险”“因环境或设计限制无法验证的部分”。

## 1. 执行摘要

这个项目是一个基于 DeepAgents、LangChain OpenAI 兼容模型和 MySQL 的制药数据分析 Agent 原型。它目前实现了一个可在脚本或 eval 中调用的数据库查询 Agent，以及一个 FastAPI 服务壳。

当前实现程度：数据库 Agent 路径可以连接 MySQL 并调用模型生成 SQL；API 服务可以启动并返回健康检查；但 HTTP 任务接口没有调用 Agent，数据分析能力没有通过 API 暴露。

最大优点：项目已经把药品、库存、销售记录的多表聚合陷阱明确写入 prompt，尤其是 `prompt/prompts.yaml:113-119` 对一对多明细表直接 JOIN 后求和会放大结果的问题有正确约束。

最大问题：生产风险最高的是模型可直接驱动 `execute_sql_query(sql)` 执行任意 SQL，代码层没有只读、表范围、超时、行数或权限隔离控制，见 `tools/mysql_tools.py:78-99`。同时 `api/server.py:33-41` 只是回显任务，没有执行 Agent。

结论：

| 判断项 | 结论 |
|---|---|
| 是否适合演示 | 适合命令行或 eval 演示，不适合 API 演示数据分析闭环 |
| 是否适合真实用户使用 | 不适合 |
| 是否适合生产部署 | 不适合 |
| 总分 | 39 / 100 |
| 成熟度等级 | Level 2 边缘：可运行 Demo，但核心服务链路不完整 |
| Agent 类型 | 多步骤 Tool-Using Agent 原型，不是可恢复、可观测的生产级 Agent |

## 2. 项目结构与执行流程

### 技术栈

- Python 3.12+，当前验证环境为 Python 3.13.9。
- FastAPI + Uvicorn：`api/server.py`。
- DeepAgents：`agent/main_agent.py:10-15`。
- LangChain OpenAI 兼容模型初始化：`agent/llm.py:9-14`。
- MySQL Connector：`tools/mysql_tools.py:4`。
- Prompt YAML：`prompt/prompts.yaml`。
- uv 项目管理和锁文件：`pyproject.toml`、`uv.lock`。

### 核心模块

| 模块 | 作用 | 证据 |
|---|---|---|
| `main.py` | 加载 `.env` 并启动 FastAPI | `main.py:1-10` |
| `api/server.py` | HTTP 健康检查和任务接口 | `api/server.py:23-45` |
| `agent/main_agent.py` | 创建 Deep Agent，挂载数据库子 Agent | `agent/main_agent.py:10-15` |
| `agent/sub_agents/db_sub_agent.py` | 注册数据库子 Agent 和三项工具 | `agent/sub_agents/db_sub_agent.py:9-18` |
| `tools/mysql_tools.py` | MySQL 连接、列表、取样、执行 SQL | `tools/mysql_tools.py:9-99` |
| `prompt/prompts.yaml` | 主 Agent 和数据库 Agent 指令 | `prompt/prompts.yaml:1-262` |
| `evals/db_agent_eval.py` | 5 个模型集成验收用例 | `evals/db_agent_eval.py:58-127` |
| `sql/db.sql` | 制药样例库结构和种子数据 | `sql/db.sql:6-138` |

### 实际执行链路

HTTP 服务链路，已验证：

用户 POST `/api/task`
→ `TaskRequest` 仅校验 `query: str` 和可选 `thread_id`
→ 生成或复用 `thread_id`
→ 返回 `status="started"` 和 `Task received: ...`
→ 结束。

证据：`api/server.py:12-20`、`api/server.py:33-41`。这条链路没有加载数据、没有调用 `main_agent`、没有调用数据库工具、没有返回分析结果。

Agent/eval 链路，已验证：

`evals/db_agent_eval.py`
→ 导入 `agent.main_agent.main_agent`
→ `main_agent.invoke({"messages": [...]})`
→ DeepAgents 主 Agent 根据 prompt 调用数据库子 Agent
→ 子 Agent 调用 `list_sql_tables` / `get_table_data` / `execute_sql_query`
→ 工具连接 MySQL 并返回 CSV 风格字符串
→ 模型生成中文表格和结论
→ eval 用关键词做粗检并写入 `output/evals/*.md`。

证据：`evals/db_agent_eval.py:136-149`、`tools/mysql_tools.py:31-99`。

### 项目包含情况

| 能力 | 当前情况 |
|---|---|
| 前端 | 无 |
| 后端 API | 有，但只含健康检查和空任务回显 |
| Agent 编排 | 有 DeepAgents 主 Agent + 子 Agent |
| 数据上传 | 无，虽然依赖中有 `python-multipart`、`aiofiles` |
| 文件解析 | 无，虽然依赖中有 pandas/openpyxl/pypdf/python-docx |
| SQL 查询 | 有，且模型可传入任意 SQL |
| Python 代码执行 | 无 |
| 图表生成 | 无 |
| 数据库 | MySQL 样例 schema 和种子数据 |
| 缓存 | 无 |
| 会话管理 | 只有 `thread_id` 字段，无持久化状态 |
| 用户认证 | 无 |
| 日志 | 无正式日志，大量 `print` |
| 测试 | 有一个 eval 脚本，无 pytest 单元测试 |
| Docker | 无 |
| 部署配置 | 无 |

## 3. 实际运行结果

| 命令 | 结果 | 说明 |
|---|---|---|
| `uv --version` | 通过 | uv 0.11.22 |
| `uv run python --version` | 通过 | Python 3.13.9 |
| `uv run python -m compileall main.py api agent tools evals` | 通过 | 语法编译通过 |
| `uv run ruff check .` | 通过 | Ruff 输出 `All checks passed!` |
| `uv run python -m mypy .` | 失败 | 环境中无 mypy：`No module named mypy` |
| `uv run python -c "import api.server; ... import agent.main_agent ..."` | 通过 | API、Agent、工具可导入 |
| `uv run python -c "from tools.mysql_tools import list_sql_tables; print(list_sql_tables())"` | 通过 | 返回 `drugs,inventory,sales_records` |
| `uv run python -c "from tools.mysql_tools import execute_sql_query; print(execute_sql_query('SELECT 1 AS ok'))"` | 通过 | SQL 工具可执行查询 |
| `uv run python -m evals.db_agent_eval` | 首次 0/5 | Windows GBK 输出无法编码 emoji，测试被 harness 捕获为失败 |
| `$env:PYTHONIOENCODING='utf-8'; uv run python -m evals.db_agent_eval` | 3/5 | 用例 1、3、4 通过，用例 2、5 未通过 |
| `uv run uvicorn api.server:app --host 127.0.0.1 --port 8017` + `/health` | 通过 | `/health` 返回 200 `{"status":"ok"}` |
| 同一服务 POST `/api/task` | 通过但无分析 | 返回 200 `{"status":"started",...}`，没有调用 Agent |
| FastAPI TestClient 空 query | 通过但不合理 | 空字符串 query 也返回 `started` |

无法验证或不适用：

- 无前端可启动。
- 无 Docker/Compose/CI 可验证。
- 无 README 启动文档可核对。
- 未执行破坏性 SQL 验证，因为会污染本地数据库；任意 SQL 风险来自代码路径和权限设计。

## 4. 评分表

| 维度 | 分值 | 得分 | 核心依据 | 主要扣分点 | 满分需要 |
|---|---:|---:|---|---|---|
| 功能完整性 | 10 | 3 | Agent 脚本和 eval 可运行，API 可启动 | API 没有调用 Agent；无上传、图表、文件解析、前端 | API 闭环、任务状态、真实分析返回 |
| 代码正确性 | 10 | 6 | compileall 和 Ruff 通过 | eval 仅 3/5；空 query 接收；失败仍 exit 0 | 可重复测试全部通过，关键参数验证 |
| 代码可读性 | 8 | 6 | 文件小、职责大体可读 | prompt 过长，工具返回字符串协议脆弱 | 结构化结果和更清晰边界 |
| 可维护性 | 8 | 4 | YAML prompt 可集中维护 | prompt 承载大量业务规则，API/Agent 未集成 | 分层服务、结构化工具返回、接口契约 |
| 架构设计 | 10 | 4 | 有 API、Agent、工具分层雏形 | 层之间没有完整业务链路，状态缺失 | 独立服务层、任务层、数据访问层 |
| Agent 实现水平 | 12 | 4 | DeepAgents + 子 Agent + 工具调用 | 无持久状态、无恢复、无审计、无停止/超时控制 | 有状态、可观测、可恢复工作流 |
| 数据分析正确性 | 10 | 5 | prompt 正确覆盖多表聚合规则 | 模型输出不稳定，SQL 与用户 Top3 要求可能不一致 | SQL 结果校验、口径校验、可追溯报告 |
| 安全性 | 8 | 1 | `.env` 未被 git 跟踪 | 任意 SQL、无认证、无权限、无限流 | 只读账号、SQL 白名单/AST 校验、认证授权 |
| 测试质量 | 8 | 2 | 有 5 个 eval 用例 | 无 pytest、无安全/异常/并发测试，失败 exit 0 | 单元、集成、API、Agent、安全测试 |
| 错误处理与可靠性 | 6 | 2 | MySQL Error 被捕获 | 无结构化错误，ValueError 未统一处理，模型/DB 无重试超时 | 明确错误类型、超时、降级 |
| 性能与并发能力 | 4 | 1 | 查询样例限制 100 行 | 任意 SQL 无 LIMIT/超时，HTTP 长任务设计缺失 | 异步任务、资源限制、查询限额 |
| 日志与可观测性 | 3 | 0 | 无正式日志 | `print` 输出 SQL 和测试内容，无 request/session/tool trace | 结构化日志、trace id、调用耗时 |
| 文档与可部署性 | 3 | 1 | 有 `.env.example` 和 uv lock | 无 README、Docker、部署说明、API 文档 | 新人可按文档安装、配置、启动、测试 |
| 总分 | 100 | 39 | 初步原型到可运行 Demo 之间 | 关键 API 链路、SQL 安全、测试可靠性不足 | 达到结构化 MVP 至少需修复 P0/P1 |

## 5. 做得好的地方

- 数据库业务 schema 清楚，`sql/db.sql:21-74` 定义了药品、库存、销售三张核心表，并设置了外键和常用索引，见 `sql/db.sql:77-81`。
- prompt 明确禁止一对多明细表直接 JOIN 后求和，`prompt/prompts.yaml:113-119` 是对真实数据分析错误的有效防护。
- 库存风险口径写得具体，`prompt/prompts.yaml:180-205` 区分了总销量口径和近 6 个月口径，避免把库存销量比误解释成可售月数。
- 数据库连接使用 context manager，`tools/mysql_tools.py:38-40`、`tools/mysql_tools.py:60-63`、`tools/mysql_tools.py:85-87` 能基本避免连接和 cursor 泄漏。
- 依赖有 `uv.lock`，项目至少具备可重复安装的基础。

## 6. 核心问题

### P0：HTTP 核心链路没有执行 Agent

* 严重程度：High
* 优先级：P0
* 涉及文件：`api/server.py`
* 相关函数或类：`create_task`
* 当前实现：`api/server.py:33-41` 只生成 `thread_id` 并返回 `Task received: ...`。
* 问题原因：API 层没有连接 `agent.main_agent.main_agent`，也没有任务执行、状态保存或结果返回。
* 可能后果：用户通过服务端接口无法完成任何数据分析；项目作为后端服务的关键路径不可用。
* 推荐修改：先做最小闭环：校验 query 非空，调用 Agent，返回最终回答；后续再拆成异步任务。
* 验证方法：POST `/api/task` 后应返回包含 SQL 查询结果或分析结论的响应，并有失败路径测试。

### P0：模型可执行任意 SQL

* 严重程度：Critical
* 优先级：P0
* 涉及文件：`tools/mysql_tools.py`
* 相关函数或类：`execute_sql_query`
* 当前实现：`tools/mysql_tools.py:78-99` 接收字符串 `sql` 并直接 `cursor.execute(sql)`，连接配置使用 `autocommit=True`，见 `tools/mysql_tools.py:17`。
* 问题原因：只在 prompt 中要求“不要执行 INSERT、UPDATE、DELETE、DROP、ALTER、TRUNCATE”，见 `prompt/prompts.yaml:110-111`，代码层没有强制只读。
* 可能后果：一旦模型被 prompt injection 或误判驱动，可能删除表、修改数据、读取不该读的数据或执行高成本查询。
* 推荐修改：使用只读数据库账号；代码层只允许单条 `SELECT`；用 SQL parser 或最小白名单拒绝 DDL/DML；强制 LIMIT、超时、最大返回行数和允许表集合。
* 验证方法：对 `DROP/UPDATE/INSERT/SELECT ... INTO/多语句` 写测试，必须被代码拒绝，不依赖 prompt。

### P1：表名工具存在 SQL 注入面

* 严重程度：High
* 优先级：P1
* 涉及文件：`tools/mysql_tools.py`
* 相关函数或类：`get_table_data`
* 当前实现：`tools/mysql_tools.py:62` 使用 `f"SELECT * FROM {table_name} LIMIT 100;"` 拼接表名。
* 问题原因：`table_name` 没有从 `SHOW TABLES` 的结果中校验，也没有标识符转义。
* 可能后果：模型或用户可传入复杂 FROM 子句、JOIN、子查询或语法片段，绕过“只看表前 100 行”的工具语义。
* 推荐修改：先调用允许表集合，只接受完全匹配的表名；用反引号安全包裹标识符。
* 验证方法：传入 `drugs JOIN sales_records ...` 或非法表名时应返回结构化拒绝。

### P1：Agent 输出缺少结果校验，可能给出看似合理的错误结论

* 严重程度：High
* 优先级：P1
* 涉及文件：`evals/db_agent_eval.py`、`prompt/prompts.yaml`
* 相关函数或类：`run_one_case`、`check_keywords`
* 当前实现：eval 只做关键词包含检查，见 `evals/db_agent_eval.py:43-55`；模型回答由 LLM 自由生成。
* 已验证现象：UTF-8 eval 中第 5 个用例执行的 SQL 按 `d.drug_id` 排序且无 `LIMIT 3`，但模型在文字中重新排出了前三名；第 2 个用例把金额转换成万元，导致关键词验收失败。
* 问题原因：SQL 结果、最终表格、用户要求之间没有机器校验。
* 可能后果：分析失败或 SQL 不符合用户意图时，模型仍可输出流畅但不可追溯的结论。
* 推荐修改：工具返回结构化 rows + SQL + row_count；最终回答前校验排序、LIMIT、列名、口径；eval 比较结构化数值而非关键词。
* 验证方法：为 Top3、单位转换、空结果、除零、错误 SQL 建固定断言。

### P1：测试失败不会让进程失败

* 严重程度：Medium
* 优先级：P1
* 涉及文件：`evals/db_agent_eval.py`
* 相关函数或类：`main`
* 当前实现：`evals/db_agent_eval.py:242-250` 打印通过率并生成报告，但无论失败数量多少都正常退出。
* 已验证现象：首次运行 0/5、UTF-8 运行 3/5，命令 exit code 都是 0。
* 问题原因：脚本没有在 `passed_count != total` 时 `raise SystemExit(1)`。
* 可能后果：CI 或人工脚本会把失败验收误判为通过。
* 推荐修改：失败时返回非零退出码；把 eval 改成 pytest 或至少加 `SystemExit(1)`。
* 验证方法：故意缺失关键词时命令 exit code 应为 1。

### P1：缺少认证、授权、限流和请求体限制

* 严重程度：High
* 优先级：P1
* 涉及文件：`api/server.py`
* 相关函数或类：`app`、`create_task`
* 当前实现：`api/server.py:9` 创建裸 FastAPI app；`api/server.py:33-41` 接口无鉴权和限流。
* 问题原因：没有用户模型、API key、session 隔离或部署安全配置。
* 可能后果：一旦 Agent 接入 API，任何人都可消耗模型额度、查询数据库或触发高成本 SQL。
* 推荐修改：至少增加 API key/JWT、用户级数据隔离、rate limit、请求大小限制。
* 验证方法：未携带凭证访问 `/api/task` 应返回 401/403。

### P1：会话 ID 只是回显，没有状态隔离

* 严重程度：High
* 优先级：P1
* 涉及文件：`api/server.py`
* 相关函数或类：`TaskRequest`、`create_task`
* 当前实现：`thread_id` 可由客户端任意传入，见 `api/server.py:14` 和 `api/server.py:35`，服务端不保存、不校验、不隔离。
* 问题原因：没有会话存储、任务状态表或用户绑定。
* 可能后果：多轮对话不能恢复；未来接入状态后容易出现跨用户 thread_id 猜测和污染。
* 推荐修改：服务端生成任务 ID，绑定用户；状态持久化到数据库或任务队列；拒绝任意复用他人 ID。
* 验证方法：两个用户不能读取或继续彼此任务。

### P1：长任务缺少超时、取消和后台执行

* 严重程度：High
* 优先级：P1
* 涉及文件：`agent/main_agent.py`、`tools/mysql_tools.py`、`api/server.py`
* 相关函数或类：`main_agent.invoke`、`execute_sql_query`
* 当前实现：Agent 调用和 MySQL 查询没有超时参数，API 也没有任务状态。
* 问题原因：当前是同步脚本式调用设计。
* 可能后果：模型调用、全表扫描或慢 SQL 会阻塞请求，造成资源耗尽。
* 推荐修改：任务队列或后台任务；数据库 statement timeout；LLM timeout；可取消任务状态。
* 验证方法：构造慢查询或模型超时，服务应在限定时间内返回可诊断错误。

### P2：日志与可观测性不足

* 严重程度：Medium
* 优先级：P2
* 涉及文件：`tools/mysql_tools.py`、`evals/db_agent_eval.py`、`agent/*.py`
* 相关函数或类：多处 `print`
* 当前实现：`tools/mysql_tools.py:35`、`tools/mysql_tools.py:57`、`tools/mysql_tools.py:82` 打印运行信息和完整 SQL。
* 问题原因：没有 logging 配置、request id、thread id、tool call id、耗时或结构化事件。
* 可能后果：问题难定位；SQL 和用户问题可能泄露到控制台或日志采集系统。
* 推荐修改：使用 `logging`，记录 request/session/task/tool id、耗时、状态；敏感内容脱敏。
* 验证方法：一次 Agent 调用应能追踪每一步工具调用和耗时。

### P2：依赖明显大于已实现功能

* 严重程度：Medium
* 优先级：P2
* 涉及文件：`pyproject.toml`
* 相关函数或类：依赖列表
* 当前实现：`pyproject.toml:8-54` 包含 Tavily、RAGFlow、pandas、openpyxl、pypdf、python-docx、markdown、pywin32、aiofiles、python-multipart 等，但仓库没有搜索、RAGFlow、上传、文件解析、PDF/Word 或图表路径。
* 问题原因：依赖按未来设想加入，而不是按当前实现加入。
* 可能后果：安装更慢、攻击面更大、维护成本更高。
* 推荐修改：删除当前未使用依赖；等实现对应功能时再加。
* 验证方法：`rg` 找不到 import 的依赖应从运行依赖移除或转入可选依赖。

### P2：prompt 承载过多业务逻辑

* 严重程度：Medium
* 优先级：P2
* 涉及文件：`prompt/prompts.yaml`
* 相关函数或类：数据库 Agent system prompt
* 当前实现：`prompt/prompts.yaml` 超过 260 行，包含 schema、SQL 示例、业务规则、风险阈值、回答规范。
* 问题原因：大量可计算、可验证的业务规则放在自然语言 prompt 中。
* 可能后果：模型不稳定执行；规则难测试；prompt injection 可绕过规则。
* 推荐修改：把 SQL 模板、口径、阈值和校验迁移到代码；prompt 只负责选择和解释。
* 验证方法：规则变化应能用单元测试验证，而不是只人工读 prompt。

### P2：缺少 README、Docker、CI 和正式测试入口

* 严重程度：Medium
* 优先级：P2
* 涉及文件：仓库根目录
* 相关函数或类：不适用
* 当前实现：根目录无 README、Dockerfile、Compose、CI、pytest 配置。
* 问题原因：项目仍处于个人实验/原型阶段。
* 可能后果：新开发者无法独立完成安装、初始化数据库、启动服务、运行验收。
* 推荐修改：补 README、数据库初始化步骤、运行命令、测试命令、环境变量说明和 CI。
* 验证方法：全新目录按 README 能跑通一次最小分析。

### P3：启动配置硬编码

* 严重程度：Low
* 优先级：P3
* 涉及文件：`api/server.py`
* 相关函数或类：`start_server`
* 当前实现：`api/server.py:44-45` 固定 `127.0.0.1:8000`。
* 问题原因：无统一配置对象。
* 可能后果：部署环境需要改代码或绕过入口。
* 推荐修改：从环境变量读取 host/port。
* 验证方法：设置 `PORT=9000` 后入口能按配置启动。

### P3：类型和结构化返回不足

* 严重程度：Low
* 优先级：P3
* 涉及文件：`tools/mysql_tools.py`、`agent/load_prompt.py`
* 相关函数或类：`get_db_config`、`_load_yaml`、工具返回值
* 当前实现：工具返回纯字符串，配置加载函数缺少明确返回类型。
* 问题原因：原型期追求快速串通 LLM。
* 可能后果：上层无法可靠判断字段、行数、错误类型。
* 推荐修改：工具返回 `{"ok": bool, "columns": [...], "rows": [...], "error": ...}`。
* 验证方法：对空结果、SQL 错误、正常结果做类型断言。

## 7. Agent 实现水平

当前更接近“多步骤 Tool-Using Agent 原型”：

- 有 Agent 框架和子 Agent：`agent/main_agent.py:10-15`。
- 有工具选择和工具调用：`agent/sub_agents/db_sub_agent.py:13-17`。
- 有 prompt 指导 SQL 口径：`prompt/prompts.yaml:83-112`。
- eval 中观察到模型会调用多个工具，再执行 SQL。

但它不是生产级 Agent：

- 没有持久任务状态。
- 没有可恢复执行。
- 没有最大执行步数、超时、取消或重试控制。
- 没有结构化执行记录。
- 没有人机确认机制。
- 没有工具权限边界，特别是 SQL 工具。
- API 层没有接入 Agent。

是否“形式大于能力”：是。项目使用了 DeepAgents 和子 Agent 结构，但可交付能力主要来自 prompt + 单个任意 SQL 工具，不是一个完整的数据分析 Agent 系统。

## 8. 数据分析正确性

数据处理可靠性：对当前三张 MySQL 表的结构化分析有一定可靠性；不支持 CSV、Excel、JSON、多文件、多 sheet、中文列名上传、大文件、异常值检测或数据质量报告。

统计计算可靠性：prompt 中对库存、销量、销售额、库存销量比的 SQL 口径较清楚，尤其避免一对多 JOIN 放大。但代码层没有验证 SQL 是否真的使用正确口径。

SQL 分析可靠性：能执行真实 SQL 并返回结果；但 SQL 完全由模型生成，缺少只读、表范围、LIMIT、超时和结果校验。

图表可靠性：无图表能力。

模型结论依据：模型通常会基于 SQL 输出生成结论，但最终报告没有强制引用 SQL、行数、原始结果 ID 或计算过程。eval 已观察到模型可改变单位、重排结果、补充业务推测。

最容易产生错误结论的地方：

1. Top N、排序、单位转换和口径解释。
2. 模型在 SQL 不完全符合用户要求时，用自然语言“补齐”。
3. 工具返回长字符串后，模型可能漏读、改写或过度解释。

## 9. 安全审计结果

### Critical

- 任意 SQL 执行：`tools/mysql_tools.py:78-99`。

### High

- API 无认证、授权、限流：`api/server.py:9`、`api/server.py:33-41`。
- 表名拼接 SQL 注入面：`tools/mysql_tools.py:62`。
- 会话 ID 客户端可控且无隔离：`api/server.py:14`、`api/server.py:35`。
- Agent 工具无超时、无取消、无资源限制：`tools/mysql_tools.py:84-96`。

### Medium

- `.env.example` 使用 `MYSQL_USER=root`、`MYSQL_PASSWORD=root` 示例，见 `.env.example:25-26`。
- 工具打印完整 SQL，可能泄露查询内容：`tools/mysql_tools.py:82`。
- 错误以字符串返回给模型和用户，缺少结构化安全边界：`tools/mysql_tools.py:49-50`、`tools/mysql_tools.py:98-99`。
- 依赖面大于实际功能，增加供应链和维护面：`pyproject.toml:8-54`。

### Low

- `.env` 文件存在于工作目录但未被 git 跟踪；`.gitignore:2-4` 已忽略它。风险是本地运维习惯，不是当前提交泄露。
- 服务默认绑定本地 `127.0.0.1`，见 `api/server.py:45`；部署时需要明确配置。

## 10. 测试缺口

当前已有测试：

- `evals/db_agent_eval.py` 含 5 个业务验收用例。
- 实际运行 UTF-8 后通过 3/5。

缺失测试：

- 无 pytest 单元测试。
- 无 API 测试。
- 无数据库工具单元测试。
- 无 SQL 安全测试。
- 无模型失败、超时、错误 SQL、空结果测试。
- 无多用户、会话隔离、并发测试。
- 无 prompt injection 测试。
- 无部署或启动测试。

最需要增加的测试：

1. `tools/test_mysql_tools.py`：只读 SQL 拒绝 DDL/DML，表名白名单，空结果和错误结构。
2. `api/test_server.py`：空 query 拒绝，任务接口实际调用 Agent 或异步任务，错误响应。
3. `evals/test_db_agent_contract.py`：固定问题的结构化 SQL/结果断言，不只查关键词。
4. `security/test_sql_policy.py`：非法 SQL、慢查询、超大结果、prompt injection。

推荐目录：

- `tests/unit/`：配置、SQL policy、工具返回结构。
- `tests/integration/`：MySQL 测试库 + Agent 工具。
- `tests/api/`：FastAPI TestClient。
- `evals/`：保留 LLM 非确定性验收，但失败必须非零退出。

## 11. 架构评价

当前架构优点：

- 文件数量少，入门成本低。
- API、Agent、工具、prompt、SQL 样例已有初步分层。
- 数据库 schema 与 prompt 对齐程度较高。

核心问题：

- 表现层和 Agent 层没有打通。
- 工具权限过大，安全边界缺失。
- 业务规则主要写在 prompt，难以测试和强制执行。
- 工具返回纯字符串，缺少结构化契约。
- 没有任务状态、会话状态、用户模型或审计日志。

是否需要重构：需要小步重构，不需要大规模重写。

应保留：

- `sql/db.sql` 的三表示例结构。
- prompt 中关于多表聚合和库存风险口径的业务知识。
- `list_sql_tables`、`get_table_data`、`execute_sql_query` 三类工具意图。

需要拆分：

- SQL 安全策略从 prompt 拆到代码。
- Agent 服务调用从 API handler 拆到 service 层。
- 工具返回从字符串拆成结构化数据模型。
- eval 逻辑从脚本打印拆成可失败的测试。

推荐目标架构：

HTTP API
→ request validation
→ task/session service
→ Agent runner
→ SQL policy validator
→ read-only DB client
→ structured tool result
→ result validator
→ response/report renderer
→ structured logs and audit events。

## 12. 改进路线图

### 第一阶段：修复正确性和安全问题

| 改进任务 | 涉及模块 | 完成标准 | 验证方式 |
|---|---|---|---|
| `/api/task` 接入 Agent 最小闭环 | `api/server.py`、`agent/main_agent.py` | 非空 query 返回真实分析或明确错误 | API 集成测试 |
| SQL 只读强制 | `tools/mysql_tools.py` | DDL/DML/多语句被拒绝 | 安全单测 |
| 表名白名单 | `tools/mysql_tools.py` | 非法表名拒绝 | 单测 |
| eval 失败返回非零退出码 | `evals/db_agent_eval.py` | 任一失败 exit 1 | 命令行验证 |
| 空 query 参数校验 | `api/server.py` | 空字符串返回 422 | API 测试 |

### 第二阶段：提高可靠性

| 改进任务 | 涉及模块 | 完成标准 | 验证方式 |
|---|---|---|---|
| 工具返回结构化结果 | `tools/`、`agent/` | rows、columns、sql、error 可机器读取 | 单元测试 |
| 增加超时和最大返回行数 | DB client、Agent runner | 慢查询和大结果被限制 | 集成测试 |
| 增加任务状态 | API、存储层 | started/running/succeeded/failed 可查询 | API 测试 |
| 明确错误类型 | API、tools、agent | 用户错误、DB 错误、模型错误可区分 | 异常路径测试 |

### 第三阶段：提高工程质量

| 改进任务 | 涉及模块 | 完成标准 | 验证方式 |
|---|---|---|---|
| 清理未使用依赖 | `pyproject.toml` | 只保留已实现功能依赖 | `uv sync` + import 测试 |
| 引入 pytest | `tests/` | 核心逻辑可本地一键测试 | `uv run pytest` |
| 结构化日志 | API、Agent、tools | request_id/task_id/tool_call 日志可追踪 | 日志快照测试 |
| README | 根目录 | 新人可初始化 DB、启动、运行 eval | 按文档重放 |
| 类型检查 | 配置和代码 | mypy/pyright 至少覆盖自有代码 | 类型检查命令 |

### 第四阶段：生产化

| 改进任务 | 涉及模块 | 完成标准 | 验证方式 |
|---|---|---|---|
| 认证和权限 | API、用户层 | 未授权不能访问数据分析 | API 安全测试 |
| 多用户隔离 | session/task/db scope | 用户只能访问自己的任务和数据 | 并发隔离测试 |
| 异步任务队列 | worker、storage | 长任务不阻塞 HTTP | 压测和超时测试 |
| 监控与审计 | logging/metrics | 模型调用、SQL、耗时、错误可观测 | 指标和日志检查 |
| Docker/部署 | Dockerfile/Compose/CI | 一键构建、健康检查、配置注入 | CI 验证 |

## 13. 最终结论

1. 这是不是一个真正的数据分析 Agent？
   是一个早期的工具调用型数据分析 Agent 原型，但不是可靠的数据分析 Agent 系统。

2. 当前最接近原型、Demo、MVP、可交付还是生产级？
   最接近可运行 Demo，但 API 层仍像原型壳。成熟度为 Level 2 边缘。

3. 代码作者目前体现出了什么工程水平？
   体现出能把 LLM、Agent 框架、MySQL 和业务 prompt 串起来的能力；但在安全边界、测试契约、API 闭环和生产工程方面经验不足。

4. 项目中最有技术含量的部分是什么？
   对多表聚合重复计算问题的识别和 prompt 约束，见 `prompt/prompts.yaml:113-119`，以及库存风险口径规则，见 `prompt/prompts.yaml:180-205`。

5. 项目中最薄弱的部分是什么？
   SQL 执行安全和 API 业务闭环。`execute_sql_query` 权限过大，`/api/task` 不执行 Agent。

6. 作为作品集项目是否有竞争力？
   有展示潜力，但当前只能展示“Agent 原型搭建”，不能展示生产级数据分析系统能力。

7. 作为面试项目应该重点展示什么？
   展示多表聚合口径、Agent 工具调用、SQL 安全改造、结构化结果校验和 eval 改进，而不是只展示模型生成的漂亮回答。

8. 如果只能改进五件事，应该优先改哪五件？
   1. 给 SQL 工具加代码层只读和白名单限制。
   2. 把 `/api/task` 接入真实 Agent 分析闭环。
   3. 把工具返回改为结构化数据，并校验最终回答。
   4. 把 eval 改成失败非零退出，并增加 pytest 测试。
   5. 增加认证、会话隔离、超时和日志。
