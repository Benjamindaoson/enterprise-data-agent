package com.jichi.salesAgent.tool;

import com.jichi.salesAgent.service.CrossBorderMetricService;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;

@Component
@RequiredArgsConstructor
@Slf4j
public class AdAnalyticsTool {

    private final CrossBorderMetricService metricService;

    @Tool("分析广告投放健康度，找出 ACOS 偏高或 ROAS 偏低的广告活动。")
    public String findHighAcosCampaigns(
            @P("开始日期，格式 yyyy-MM-dd；为空时默认最近 30 天") String startDate,
            @P("结束日期，格式 yyyy-MM-dd；为空时默认今天") String endDate,
            @P("店铺名称，可为空") String storeName,
            @P("ACOS 阈值百分比，例如 35 表示 35%；默认 35") double thresholdPercent) {

        try {
            LocalDate end = parseDate(endDate, LocalDate.now());
            LocalDate start = parseDate(startDate, end.minusDays(30));
            BigDecimal threshold = BigDecimal.valueOf(thresholdPercent <= 0 ? 35 : thresholdPercent);
            var rows = metricService.highAcosCampaigns(storeName, start, end, threshold);
            if (rows.isEmpty()) {
                return "没有发现 ACOS 高于 %.2f%% 的广告活动。".formatted(threshold);
            }
            StringBuilder sb = new StringBuilder("高 ACOS 广告活动：\n");
            for (int i = 0; i < rows.size(); i++) {
                var row = rows.get(i);
                sb.append("%d. %s（%s）：花费 %,.2f，广告销售额 %,.2f，ACOS %.2f%%，ROAS %.2f\n"
                        .formatted(i + 1, row.campaignName(), row.channel(), row.spend(), row.sales(),
                                row.acos(), row.roas()));
            }
            sb.append("\n建议：先暂停或降价测试高 ACOS 活动，再检查关键词匹配、商品转化率和库存状态。");
            return sb.toString();
        } catch (Exception e) {
            log.error("findHighAcosCampaigns failed", e);
            return "广告健康度分析失败。请确认日期格式为 yyyy-MM-dd。";
        }
    }

    private LocalDate parseDate(String value, LocalDate fallback) {
        return value == null || value.isBlank() ? fallback : LocalDate.parse(value.trim());
    }
}
