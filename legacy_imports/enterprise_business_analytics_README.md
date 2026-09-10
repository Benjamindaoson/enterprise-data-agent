# 企业经营数据智能分析 Agent

这是一个面向企业经营数据分析场景的 AI Agent 项目快照，包含 Java 与 Python 两套实现路径。

## 项目定位

项目目标是把订单、商品、广告、库存、退款、评价等经营数据转化为可对话、可查询、可解释的智能分析能力。它不是简单聊天机器人，而是围绕经营指标、业务问题和数据工具调用构建的 Agent 原型。

## 主要内容

- `crossborder-ops-agent-java/`：Java 21 + Spring Boot + LangChain4j 后端，配套 Vue 3 + ECharts 前端。
- `crossborder-ops-agent-python/`：Python + FastAPI 方向的生产化后端尝试，包含 SQLAlchemy、Alembic、Redis、OpenTelemetry、OIDC/JWKS、Eval 和 Docker 配置。
- `course/`、`docs/`、`openspec/`：项目训练材料、架构说明和规格设计。

## 核心能力

- 经营指标问答
- 订单、商品、广告、库存、退款、评价等业务域建模
- Agent 工具调用与业务查询链路
- 图表化结果返回
- 前后端分离交互界面
- Java 教学版与 Python 生产化版的对照实现

## 技术栈

- Java 21
- Spring Boot
- LangChain4j
- Vue 3
- ECharts
- Python
- FastAPI
- SQLAlchemy
- Alembic
- Redis
- Docker
- OpenTelemetry

## 上传范围说明

本仓库是整理后的私有快照。上传时已排除以下内容：

- `.tools/` 本地 JDK、Maven 等工具目录
- `.venv/`、`node_modules/` 等依赖目录
- `archive-original-materials/`、`archive-python-teaching-backend/` 等历史归档
- 缓存、日志、编译产物、临时数据库和大文件
- 真实环境变量文件和明显敏感内容

## 适合继续投入的方向

1. 选择 Java 或 Python 其中一条作为主线，避免双版本长期分叉。
2. 把业务数据模型、Agent 工具、图表输出协议沉淀为稳定接口。
3. 补齐统一的本地启动说明、测试流程和示例数据。
4. 如果作为作品集展示，应优先保留“企业经营数据智能分析”的业务闭环，而不是课程归档材料。
