package com.jichi.salesAgent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jichi.salesAgent.agent.SalesAgent;
import com.jichi.salesAgent.tool.AdAnalyticsTool;
import com.jichi.salesAgent.tool.OrderAnalyticsTool;
import com.jichi.salesAgent.tool.RefundAnalyticsTool;
import com.jichi.salesAgent.tool.VisualPayloadTool;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.io.IOException;
import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

@SpringBootTest
class SalesAgentSmokeTest {

    @Autowired
    private SalesAgent salesAgent;

    @Autowired
    private OrderAnalyticsTool orderAnalyticsTool;

    @Autowired
    private RefundAnalyticsTool refundAnalyticsTool;

    @Autowired
    private AdAnalyticsTool adAnalyticsTool;

    @Autowired
    private VisualPayloadTool visualPayloadTool;

    private final ObjectMapper objectMapper = new ObjectMapper();

    // chat() 的第三个参数 today 对应 System Prompt 里的 {{today}} 变量
    private final String today = LocalDate.now().toString();

    @Test
    void smokeTest() {
        assumeTrue(hasLlmApiKey(), "LLM_API_KEY is not set; skipping live LLM smoke test.");
        String response = salesAgent.chat(
                "test-session-001",
                "你好，你能做什么？",
                today);
        System.out.println("Agent 回答：" + response);
    }

    @Test
    void toolCallTest() {
        assumeTrue(hasLlmApiKey(), "LLM_API_KEY is not set; skipping live LLM tool-call test.");
        String response = salesAgent.chat(
                "test-session-002",
                "近6个月的月度销售趋势是什么？",
                today);
        System.out.println("Agent 回答：" + response);
    }

    @Test
    void businessSummaryIncludesAverageOrderProfit() {
        String response = orderAnalyticsTool.summarizeBusiness("2026-06-03", "2026-07-03", null);

        assertTrue(response.contains("平均订单利润"));
        assertTrue(response.contains("2,849.94"));
    }

    @Test
    void refundRiskToolReturnsSeededRefundSkus() {
        String response = refundAnalyticsTool.findRefundRiskSkus("2026-06-03", "2026-07-03", null, 3);

        assertTrue(response.contains("退款风险 SKU 排名"));
        assertTrue(response.contains("YM-US-2001"));
        assertTrue(response.contains("EB-US-1001"));
    }

    @Test
    void adToolReturnsAcosAndRoasForSeededCampaign() {
        String response = adAnalyticsTool.findHighAcosCampaigns("2026-06-03", "2026-07-03", null, 35);

        assertTrue(response.contains("US Earbuds Prime Search"));
        assertTrue(response.contains("ACOS"));
        assertTrue(response.contains("ROAS"));
    }

    @Test
    void visualPayloadHasEchartsStructure() throws IOException {
        String response = visualPayloadTool.generateBusinessTrendChart(6, null, "测试趋势图");

        assertTrue(response.startsWith("VISUAL_PAYLOAD:"));
        JsonNode payload = objectMapper.readTree(response.substring("VISUAL_PAYLOAD:".length()));
        assertTrue(payload.path("kind").asText().equals("echarts"));
        assertTrue(payload.path("option").path("xAxis").path("data").isArray());
        assertTrue(payload.path("option").path("series").isArray());
    }

    private boolean hasLlmApiKey() {
        return System.getenv("LLM_API_KEY") != null && !System.getenv("LLM_API_KEY").isBlank();
    }
}
