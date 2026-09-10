package com.jichi.salesAgent.service;

import com.jichi.salesAgent.entity.SkuProduct;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class ListingOptimizationService {

    private final CrossBorderMetricService metricService;

    public String generateListing(String skuCode, String marketplace, String locale, String sellingPoint) {
        SkuProduct sku = metricService.findSku(skuCode).orElse(null);
        if (sku == null) {
            return "未找到 SKU " + skuCode + "。请先确认商品编码是否存在于课堂演示数据中。";
        }
        String market = blankToDefault(marketplace, sku.getTargetMarketplace());
        String lang = blankToDefault(locale, "en-US");
        String point = blankToDefault(sellingPoint, "stable quality, fast delivery, and practical daily use");

        return """
                Listing 优化草案
                - SKU：%s
                - 平台/站点：%s
                - 语言：%s
                - 新标题：%s for %s | Reliable Quality and Fast Cross-border Delivery
                - 五点描述：
                  1. Built for %s shoppers with clear value and practical use cases.
                  2. Highlights %s while avoiding unsupported claims.
                  3. Adds searchable category keywords: %s, %s, cross-border ready.
                  4. Reduces售后误解：在详情页明确尺寸、材质、适配范围和包裹内容。
                  5. 运营动作：同步检查差评关键词，并把高频问题写入 FAQ。
                - 搜索关键词：%s, %s, best value, fast shipping, %s
                """.formatted(
                sku.getSkuCode(),
                market,
                lang,
                sku.getTitle(),
                sku.getCategory(),
                market,
                point,
                sku.getCategory(),
                sku.getSkuCode(),
                sku.getCategory().toLowerCase(),
                sku.getSkuCode().toLowerCase(),
                market.toLowerCase());
    }

    private String blankToDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }
}
