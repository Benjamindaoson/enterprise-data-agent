package com.jichi.salesAgent.controller;

import com.jichi.salesAgent.tool.*;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/test/tool")
@RequiredArgsConstructor
public class ToolTestController {

    private final OrderAnalyticsTool orderAnalyticsTool;
    private final RefundAnalyticsTool refundAnalyticsTool;
    private final AdAnalyticsTool adAnalyticsTool;
    private final ReviewInsightTool reviewInsightTool;
    private final ListingOptimizationTool listingOptimizationTool;
    private final VisualPayloadTool visualPayloadTool;

    record SummaryRequest(String startDate, String endDate, String storeName) {}
    record TrendRequest(int months, String storeName, String title) {}
    record RefundRequest(String startDate, String endDate, String storeName, int topN) {}
    record AdRequest(String startDate, String endDate, String storeName, double thresholdPercent) {}
    record ReviewRequest(String storeName, int days) {}
    record ListingRequest(String skuCode, String marketplace, String locale, String sellingPoint) {}

    @PostMapping("/business-summary")
    public String businessSummary(@RequestBody SummaryRequest req) {
        return orderAnalyticsTool.summarizeBusiness(req.startDate(), req.endDate(), req.storeName());
    }

    @PostMapping("/business-trend-chart")
    public String businessTrendChart(@RequestBody TrendRequest req) {
        return visualPayloadTool.generateBusinessTrendChart(req.months(), req.storeName(), req.title());
    }

    @PostMapping("/store-comparison-chart")
    public String storeComparisonChart(@RequestBody SummaryRequest req) {
        return visualPayloadTool.generateStoreComparisonBarChart(req.startDate(), req.endDate(), "店铺经营对比");
    }

    @PostMapping("/refund-risks")
    public String refundRisks(@RequestBody RefundRequest req) {
        return refundAnalyticsTool.findRefundRiskSkus(req.startDate(), req.endDate(), req.storeName(), req.topN());
    }

    @PostMapping("/high-acos-campaigns")
    public String highAcosCampaigns(@RequestBody AdRequest req) {
        return adAnalyticsTool.findHighAcosCampaigns(
                req.startDate(), req.endDate(), req.storeName(), req.thresholdPercent());
    }

    @PostMapping("/review-insights")
    public String reviewInsights(@RequestBody ReviewRequest req) {
        return reviewInsightTool.summarizeNegativeReviews(req.storeName(), req.days());
    }

    @PostMapping("/listing-draft")
    public String listingDraft(@RequestBody ListingRequest req) {
        return listingOptimizationTool.generateListingDraft(
                req.skuCode(), req.marketplace(), req.locale(), req.sellingPoint());
    }
}
