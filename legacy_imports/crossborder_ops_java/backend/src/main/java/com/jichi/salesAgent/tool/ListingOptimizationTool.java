package com.jichi.salesAgent.tool;

import com.jichi.salesAgent.service.ListingOptimizationService;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class ListingOptimizationTool {

    private final ListingOptimizationService listingOptimizationService;

    @Tool("根据 SKU、平台站点、语言和卖点生成跨境电商 Listing 优化草案，包括标题、五点描述和关键词。")
    public String generateListingDraft(
            @P("SKU 编码，例如 EB-US-1001") String skuCode,
            @P("平台或站点，例如 Amazon US、Amazon DE、TikTok Shop UK") String marketplace,
            @P("语言区域，例如 en-US、de-DE、en-GB") String locale,
            @P("希望强化的卖点，可为空") String sellingPoint) {

        return listingOptimizationService.generateListing(skuCode, marketplace, locale, sellingPoint);
    }
}
