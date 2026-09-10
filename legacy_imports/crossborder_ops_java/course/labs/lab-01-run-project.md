# Lab 01：跑起来并观察系统

## 目标

确认项目能在本机运行，并理解“前端问题 -> 后端 Agent -> 工具 -> 数据库 -> 前端回复”的基本体验。

## 操作

1. 启动 MySQL 和 Redis：

```powershell
docker compose up -d
```

2. 启动后端：

```powershell
cd backend
mvn spring-boot:run
```

3. 启动前端：

```powershell
cd frontend
pnpm install
pnpm dev
```

4. 打开：

```text
http://127.0.0.1:5173
```

5. 用账号 `3` 登录，提问：

```text
分析最近30天的经营概览
```

## 自检

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File course\scripts\smoke-check.ps1
```

## 验收标准

- health 返回 `UP`。
- 登录返回用户信息。
- 经营概览有净销售额、利润、退款率。
- 图表接口返回 `VISUAL_PAYLOAD:`。

## 思考题

- 为什么经营指标不应该完全交给大模型自由编造？
- 这个项目里，哪些结果来自数据库计算，哪些结果来自大模型组织语言？

## 任务分层

- 必做：完成登录、提问和自检脚本。
- 进阶：记录一次图表问题的前后端响应。
- 挑战：解释一次 Agent 工具调用链路。

## 提交物

1. 前端登录后的截图或文字记录。
2. 一次经营概览问题和返回结果。
3. `smoke-check.ps1` 运行结果。
4. 100 字以内说明：哪些结果来自数据库，哪些结果来自大模型。
