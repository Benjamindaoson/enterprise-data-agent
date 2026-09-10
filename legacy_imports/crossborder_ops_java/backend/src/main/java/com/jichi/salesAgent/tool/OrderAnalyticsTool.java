package com.jichi.salesAgent.tool;

import com.jichi.salesAgent.service.CrossBorderMetricService;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDate;

@Component
@RequiredArgsConstructor
@Slf4j
public class OrderAnalyticsTool {

    private final CrossBorderMetricService metricService;

    @Tool("查询跨境电商店铺或全公司的经营概览，包括净销售额、利润、利润率、平均订单利润、退款金额、退款率、订单数和销量。")
    public String summarizeBusiness(
            @P("开始日期，格式 yyyy-MM-dd；为空时默认最近 30 天") String startDate,
            @P("结束日期，格式 yyyy-MM-dd；为空时默认今天") String endDate,
            @P("店铺名称，可为空；例如 Amazon US Store、TikTok UK Store") String storeName) {

        log.info("tool summarizeBusiness start={}, end={}, store={}", startDate, endDate, storeName);
        try {
            LocalDate end = parseDate(endDate, LocalDate.now());
            LocalDate start = parseDate(startDate, end.minusDays(30));
            var summary = metricService.summarizeBusiness(storeName, start, end);
            return """
                    经营概览（%s，%s 至 %s）
                    - 净销售额：%,.2f
                    - 毛利润：%,.2f
                    - 利润率：%.2f%%
                    - 平均订单利润：%,.2f
                    - 退款金额：%,.2f
                    - 退款率：%.2f%%
                    - 订单数：%d
                    - 销售件数：%d

                    初步判断：%s
                    """.formatted(
                    summary.storeName(), summary.startDate(), summary.endDate(),
                    summary.netSales(), summary.profit(), summary.profitRate(),
                    summary.averageOrderProfit(), summary.refundAmount(), summary.refundRate(),
                    summary.orders(), summary.units(),
                    summary.profitRate().doubleValue() < 18
                            ? "利润率偏低，建议优先检查广告 ACOS、退款 SKU 和物流成本。"
                            : "整体利润率可接受，建议继续拆分广告、退款和评论数据寻找增长点。");
        } catch (Exception e) {
            log.error("summarizeBusiness failed", e);
            return "经营概览查询失败。请确认日期格式为 yyyy-MM-dd，并检查演示数据库是否已初始化。";
        }
    }

    @Tool("查询经营趋势，用于回答近几个月销售额和利润变化。若用户要求画趋势图，请优先使用可视化工具。")
    public String monthlyTrend(
            @P("最近几个月，默认 6，最大 18") int months,
            @P("店铺名称，可为空") String storeName) {

        int safeMonths = months <= 0 ? 6 : Math.min(months, 18);
        var rows = metricService.monthlyTrend(storeName, safeMonths);
        if (rows.isEmpty()) {
            return "暂无趋势数据。";
        }
        StringBuilder sb = new StringBuilder("月度经营趋势：\n");
        rows.forEach(row -> sb.append("- ")
                .append(row.month())
                .append("：净销售额 ")
                .append(row.netSales())
                .append("，利润 ")
                .append(row.profit())
                .append('\n'));
        return sb.toString();
    }

    private LocalDate parseDate(String value, LocalDate fallback) {
        return value == null || value.isBlank() ? fallback : LocalDate.parse(value.trim());
    }
}
