# Lab 02：读懂 Agent、Tool、Service 链路

## 目标

沿着一次经营分析问题，读懂核心调用链路。

## 阅读顺序

1. `frontend/src/stores/chat.js`
   - 看前端如何发起聊天请求。
   - 看流式响应如何进入消息列表。

2. `backend/src/main/java/com/jichi/salesAgent/controller`
   - 看普通聊天和 SSE 聊天入口。

3. `backend/src/main/java/com/jichi/salesAgent/agent`
   - 看系统提示词如何约束 Agent。
   - 看 Agent 如何声明可用工具。

4. `backend/src/main/java/com/jichi/salesAgent/tool`
   - 看 `OrderAnalyticsTool`、`RefundAnalyticsTool`、`AdAnalyticsTool`、`VisualPayloadTool`。
   - 注意工具方法的入参应该简单、明确、可验证。

5. `backend/src/main/java/com/jichi/salesAgent/service/CrossBorderMetricService.java`
   - 看指标口径和权限范围在哪里计算。

6. `backend/src/main/resources/db/schema.sql`
   - 对照表结构理解数据来源。

## 课堂任务

画出下面问题的调用链：

```text
画出近6个月净销售额和利润趋势图
```

建议格式：

```text
ChatView -> chat store -> /agent/chat/stream -> Agent -> VisualPayloadTool -> CrossBorderMetricService -> Repository -> MySQL
```

## 验收标准

学生能说清楚：

- Agent 不直接查数据库。
- Tool 是模型和业务服务之间的边界。
- Service 才是指标口径的核心位置。
- 图表不是模型随便写 JSON，而是工具返回结构化 payload。

## 任务分层

- 必做：画出一个问题的完整调用链。
- 进阶：指出每一层对应的代码文件。
- 挑战：说明如果 Tool 参数设计不好，会带来什么业务风险。

## 提交物

1. 一张调用链图或文本链路。
2. 每一层对应的文件路径。
3. 200 字以内说明：为什么业务指标要放在 Service，而不是让模型生成。
