# Lab 03 参考答案：平均订单利润

这个参考实现只做一件事：在经营概览里增加“平均订单利润”。

当前仓库是完整演示版，下面的代码已经存在于主源码中。学生练习时可以阅读它，也可以在 starter 版本或删除已有实现后的本地副本中重新完成。

```text
平均订单利润 = 毛利润 / 订单数
```

## 为什么选这个题

- 指标简单，学生容易理解。
- 不需要新增表。
- 能完整覆盖 Test -> Service -> Tool -> 输出验证。
- 能体现企业 AI 项目的关键原则：指标由 Java 服务计算，不交给大模型编造。

## 第一步：用测试锁定目标状态

修改：

```text
backend/src/test/java/com/jichi/salesAgent/SalesAgentSmokeTest.java
```

新增测试：

```java
@Test
void businessSummaryIncludesAverageOrderProfit() {
    String response = orderAnalyticsTool.summarizeBusiness("2026-06-03", "2026-07-03", null);

    assertTrue(response.contains("平均订单利润"));
    assertTrue(response.contains("2,849.94"));
}
```

运行：

```powershell
cd backend
mvn -Dtest=SalesAgentSmokeTest#businessSummaryIncludesAverageOrderProfit test
```

在 starter 版本中，预期结果应该失败，因为输出还没有“平均订单利润”。在当前完整演示版中，这个测试应该通过，用来证明目标状态已经具备。

## 第二步：在 Service 里计算指标

修改：

```text
backend/src/main/java/com/jichi/salesAgent/service/CrossBorderMetricService.java
```

核心逻辑：

```java
BigDecimal averageOrderProfit = orders == 0
        ? BigDecimal.ZERO
        : profit.divide(BigDecimal.valueOf(orders), 2, RoundingMode.HALF_UP);
```

注意点：

- 订单数为 0 时返回 0，避免除零。
- 保留 2 位小数。
- 指标放在 `BusinessSummary` 里，让 Tool 只负责展示。

## 第三步：在 Tool 输出里展示

修改：

```text
backend/src/main/java/com/jichi/salesAgent/tool/OrderAnalyticsTool.java
```

在经营概览中新增一行：

```text
- 平均订单利润：%,.2f
```

这样 Agent 调用工具时，指标会自然出现在回答里。

## 第四步：跑验证

运行单测：

```powershell
cd backend
mvn -Dtest=SalesAgentSmokeTest#businessSummaryIncludesAverageOrderProfit test
```

运行完整后端测试：

```powershell
cd backend
mvn test
```

运行自检：

```powershell
powershell -ExecutionPolicy Bypass -File course\scripts\smoke-check.ps1
```

## 你需要讲清楚的改造路径

这个练习重点不是公式，而是改造路径：

```text
需求 -> 失败测试 -> Service 指标口径 -> Tool 输出 -> 验证
```

学生要记住：经营指标必须由确定性代码计算。大模型可以解释、总结、给建议，但不能凭空生成关键财务指标。
