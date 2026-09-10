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
public class RefundAnalyticsTool {

    private final CrossBorderMetricService metricService;

    @Tool("找出退款风险最高的 SKU，适合分析退货率、差评风险、产品质量或描述问题。")
    public String findRefundRiskSkus(
            @P("开始日期，格式 yyyy-MM-dd；为空时默认最近 60 天") String startDate,
            @P("结束日期，格式 yyyy-MM-dd；为空时默认今天") String endDate,
            @P("店铺名称，可为空") String storeName,
            @P("返回前 N 个 SKU，默认 5") int topN) {

        try {
            LocalDate end = parseDate(endDate, LocalDate.now());
            LocalDate start = parseDate(startDate, end.minusDays(60));
            int n = topN <= 0 ? 5 : Math.min(topN, 20);
            var rows = metricService.refundRisks(storeName, start, end, n);
            if (rows.isEmpty()) {
                return "该时间段内没有退款记录。";
            }
            StringBuilder sb = new StringBuilder("退款风险 SKU 排名：\n");
            for (int i = 0; i < rows.size(); i++) {
                var row = rows.get(i);
                sb.append("%d. %s [%s]：退款 %d 单，销量 %d 件，退款率 %.2f%%，退款金额 %,.2f\n"
                        .formatted(i + 1, row.title(), row.skuCode(), row.refunds(), row.units(),
                                row.refundRate(), row.refundAmount()));
            }
            sb.append("\n建议：优先检查排名靠前 SKU 的差评关键词、Listing 描述准确性、包装和物流破损问题。");
            return sb.toString();
        } catch (Exception e) {
            log.error("findRefundRiskSkus failed", e);
            return "退款风险分析失败。请确认日期格式为 yyyy-MM-dd。";
        }
    }

    private LocalDate parseDate(String value, LocalDate fallback) {
        return value == null || value.isBlank() ? fallback : LocalDate.parse(value.trim());
    }
}
