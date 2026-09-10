package com.jichi.salesAgent.tool;

import com.jichi.salesAgent.service.CrossBorderMetricService;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class ReviewInsightTool {

    private final CrossBorderMetricService metricService;

    @Tool("分析近期低星评论，归纳物流、质量、尺寸、描述不一致等客户反馈主题。")
    public String summarizeNegativeReviews(
            @P("店铺名称，可为空") String storeName,
            @P("最近多少天，默认 90") int days) {

        var insight = metricService.reviewInsight(storeName, days <= 0 ? 90 : days);
        if (insight.negativeReviewCount() == 0) {
            return "近期没有低星评论。";
        }
        StringBuilder sb = new StringBuilder("低星评论洞察（")
                .append(insight.storeName())
                .append("，自 ")
                .append(insight.since())
                .append(" 起）：\n")
                .append("- 低星评论数：")
                .append(insight.negativeReviewCount())
                .append('\n');
        insight.themes().forEach((theme, count) -> sb.append("- ").append(theme).append("：").append(count).append(" 条\n"));
        sb.append("\n样例评论：\n");
        insight.samples().forEach(sample -> sb.append("- ").append(sample).append('\n'));
        sb.append("\n建议：把高频主题同步到 Listing FAQ、质检清单和客服话术。");
        return sb.toString();
    }
}
