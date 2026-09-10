package com.jichi.salesAgent.tool;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jichi.salesAgent.service.CrossBorderMetricService;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.time.LocalDate;

@Component
@RequiredArgsConstructor
@Slf4j
public class VisualPayloadTool {

    private final CrossBorderMetricService metricService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Tool("生成跨境经营趋势图的 ECharts 可视化 payload。用户要求画图、趋势图、折线图时使用。")
    public String generateBusinessTrendChart(
            @P("最近几个月，默认 6，最大 18") int months,
            @P("店铺名称，可为空") String storeName,
            @P("图表标题，可为空") String title) {

        try {
            int safeMonths = months <= 0 ? 6 : Math.min(months, 18);
            var rows = metricService.monthlyTrend(storeName, safeMonths);
            if (rows.isEmpty()) {
                return "暂无趋势数据，无法生成图表。";
            }
            List<String> xAxis = rows.stream().map(CrossBorderMetricService.MonthlyTrend::month).toList();
            List<Number> sales = rows.stream().map(row -> (Number) row.netSales()).toList();
            List<Number> profit = rows.stream().map(row -> (Number) row.profit()).toList();

            Map<String, Object> option = new LinkedHashMap<>();
            option.put("title", Map.of("text", title == null || title.isBlank() ? "跨境经营趋势" : title));
            option.put("tooltip", Map.of("trigger", "axis"));
            option.put("legend", Map.of("data", List.of("净销售额", "利润")));
            option.put("xAxis", Map.of("type", "category", "data", xAxis));
            option.put("yAxis", Map.of("type", "value", "name", "金额"));
            option.put("series", List.of(
                    Map.of("type", "line", "name", "净销售额", "smooth", true, "data", sales),
                    Map.of("type", "line", "name", "利润", "smooth", true, "data", profit)
            ));

            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("kind", "echarts");
            payload.put("title", title);
            payload.put("option", option);
            return "VISUAL_PAYLOAD:" + objectMapper.writeValueAsString(payload);
        } catch (Exception e) {
            log.error("generateBusinessTrendChart failed", e);
            return "生成图表数据失败。";
        }
    }

    @Tool("生成各店铺经营对比柱状图的 ECharts 可视化 payload。用户要求店铺排名、店铺对比、柱状图时使用。")
    public String generateStoreComparisonBarChart(
            @P("开始日期，格式 yyyy-MM-dd；为空时默认最近 30 天") String startDate,
            @P("结束日期，格式 yyyy-MM-dd；为空时默认今天") String endDate,
            @P("图表标题，可为空") String title) {

        try {
            LocalDate end = parseDate(endDate, LocalDate.now());
            LocalDate start = parseDate(startDate, end.minusDays(30));
            var rows = metricService.compareStores(start, end);
            if (rows.isEmpty()) {
                return "暂无店铺对比数据，无法生成图表。";
            }
            List<String> xAxis = rows.stream().map(CrossBorderMetricService.StoreComparison::storeName).toList();
            List<Number> sales = rows.stream().map(row -> (Number) row.netSales()).toList();
            List<Number> profit = rows.stream().map(row -> (Number) row.profit()).toList();

            Map<String, Object> option = new LinkedHashMap<>();
            option.put("title", Map.of("text", title == null || title.isBlank() ? "店铺经营对比" : title));
            option.put("tooltip", Map.of("trigger", "axis"));
            option.put("legend", Map.of("data", List.of("净销售额", "利润")));
            option.put("xAxis", Map.of("type", "category", "data", xAxis, "axisLabel", Map.of("rotate", 18)));
            option.put("yAxis", Map.of("type", "value", "name", "金额"));
            option.put("series", List.of(
                    Map.of("type", "bar", "name", "净销售额", "data", sales),
                    Map.of("type", "bar", "name", "利润", "data", profit)
            ));

            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("kind", "echarts");
            payload.put("title", title);
            payload.put("option", option);
            return "VISUAL_PAYLOAD:" + objectMapper.writeValueAsString(payload);
        } catch (Exception e) {
            log.error("generateStoreComparisonBarChart failed", e);
            return "生成店铺对比图失败。";
        }
    }

    private LocalDate parseDate(String value, LocalDate fallback) {
        return value == null || value.isBlank() ? fallback : LocalDate.parse(value.trim());
    }
}
