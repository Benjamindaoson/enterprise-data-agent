package com.jichi.salesAgent.agent;

import com.jichi.salesAgent.memory.MysqlChatMemoryStore;
import com.jichi.salesAgent.tool.*;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.StreamingChatModel;
import dev.langchain4j.service.AiServices;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@RequiredArgsConstructor
@Slf4j
public class SalesAgentConfig {

    private final ChatModel chatLanguageModel;
    private final StreamingChatModel streamingChatLanguageModel;
    private final OrderAnalyticsTool orderAnalyticsTool;
    private final RefundAnalyticsTool refundAnalyticsTool;
    private final AdAnalyticsTool adAnalyticsTool;
    private final ReviewInsightTool reviewInsightTool;
    private final ListingOptimizationTool listingOptimizationTool;
    private final VisualPayloadTool visualPayloadTool;
    private final MysqlChatMemoryStore chatMemoryStore;

    @Bean
    public SalesAgent salesAgent() {
        return AiServices.builder(SalesAgent.class)
                .chatModel(chatLanguageModel)
                .streamingChatModel(streamingChatLanguageModel)
                .tools(orderAnalyticsTool,
                        refundAnalyticsTool,
                        adAnalyticsTool,
                        reviewInsightTool,
                        listingOptimizationTool,
                        visualPayloadTool)
                .beforeToolExecution(exec ->
                        log.info("tool start | name={} | args={}",
                                exec.request().name(),
                                exec.request().arguments()))
                .afterToolExecution(exec ->
                        log.info("tool done | name={} | resultLength={}",
                                exec.request().name(),
                                exec.result() != null ? exec.result().length() : 0))
                .chatMemoryProvider(memoryId ->
                        MessageWindowChatMemory.builder()
                                .id(memoryId)
                                .maxMessages(20)
                                .chatMemoryStore(chatMemoryStore)
                                .build())
                .build();
    }
}
