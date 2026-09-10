package com.jichi.salesAgent.service;

import com.jichi.salesAgent.entity.*;
import com.jichi.salesAgent.repository.*;
import com.jichi.salesAgent.security.UserContext;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class CrossBorderMetricService {

    private final StoreRepository storeRepository;
    private final SkuProductRepository skuProductRepository;
    private final CommerceOrderRepository orderRepository;
    private final RefundRecordRepository refundRepository;
    private final AdCampaignRepository campaignRepository;
    private final AdDailyReportRepository adReportRepository;
    private final ProductReviewRepository reviewRepository;

    public BusinessSummary summarizeBusiness(String storeName, LocalDate startDate, LocalDate endDate) {
        Long storeId = resolveScopedStoreId(storeName);
        Object[] row = summaryRow(storeId, startDate, endDate);
        BigDecimal netSales = decimal(row[0]);
        BigDecimal profit = decimal(row[1]);
        long units = number(row[2]).longValue();
        long orders = number(row[3]).longValue();
        BigDecimal profitRate = percent(profit, netSales);
        BigDecimal averageOrderProfit = orders == 0
                ? BigDecimal.ZERO
                : profit.divide(BigDecimal.valueOf(orders), 2, RoundingMode.HALF_UP);
        BigDecimal refundAmount = refundRows(storeId, startDate, endDate).stream()
                .map(RefundRecord::getRefundAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal refundRate = percent(refundAmount, netSales);

        return new BusinessSummary(storeId, storeName(storeId), startDate, endDate, netSales, profit,
                profitRate, averageOrderProfit, refundAmount, refundRate, units, orders);
    }

    public List<MonthlyTrend> monthlyTrend(String storeName, int months) {
        Long storeId = resolveScopedStoreId(storeName);
        int safeMonths = Math.max(1, Math.min(months, 18));
        LocalDate end = LocalDate.now();
        LocalDate start = end.minusMonths(safeMonths - 1L).withDayOfMonth(1);
        return orderRepository.monthlyTrend(storeId, start, end).stream()
                .map(row -> new MonthlyTrend(String.valueOf(row[0]), decimal(row[1]), decimal(row[2])))
                .toList();
    }

    public List<StoreComparison> compareStores(LocalDate startDate, LocalDate endDate) {
        UserContext.UserInfo user = UserContext.get();
        List<Store> stores = storeRepository.findAll().stream()
                .filter(store -> user == null || user.isDirector() || Objects.equals(user.storeId(), store.getId()))
                .toList();
        return stores.stream()
                .map(store -> {
                    Object[] row = summaryRow(store.getId(), startDate, endDate);
                    BigDecimal netSales = decimal(row[0]);
                    BigDecimal profit = decimal(row[1]);
                    return new StoreComparison(store.getId(), store.getName(), netSales, profit, percent(profit, netSales));
                })
                .sorted(Comparator.comparing(StoreComparison::netSales).reversed())
                .toList();
    }

    public List<SkuRefundRisk> refundRisks(String storeName, LocalDate startDate, LocalDate endDate, int topN) {
        Long storeId = resolveScopedStoreId(storeName);
        Map<Long, SkuProduct> skuMap = skuProductRepository.findAll().stream()
                .collect(Collectors.toMap(SkuProduct::getId, Function.identity()));
        Map<Long, Long> orderedUnits = orderRepository.summarizeBySku(storeId, startDate, endDate).stream()
                .collect(Collectors.toMap(row -> number(row[0]).longValue(), row -> number(row[1]).longValue()));

        return refundRows(storeId, startDate, endDate).stream()
                .collect(Collectors.groupingBy(RefundRecord::getSkuId,
                        Collectors.reducing(BigDecimal.ZERO, RefundRecord::getRefundAmount, BigDecimal::add)))
                .entrySet().stream()
                .map(entry -> {
                    SkuProduct sku = skuMap.get(entry.getKey());
                    long units = Math.max(orderedUnits.getOrDefault(entry.getKey(), 0L), 1L);
                    long refunds = refundRows(storeId, startDate, endDate).stream()
                            .filter(r -> Objects.equals(r.getSkuId(), entry.getKey()))
                            .count();
                    BigDecimal rate = BigDecimal.valueOf(refunds * 100.0 / units).setScale(2, RoundingMode.HALF_UP);
                    return new SkuRefundRisk(
                            entry.getKey(),
                            sku == null ? "UNKNOWN" : sku.getSkuCode(),
                            sku == null ? "Unknown SKU" : sku.getTitle(),
                            refunds,
                            units,
                            rate,
                            entry.getValue());
                })
                .sorted(Comparator.comparing(SkuRefundRisk::refundRate).reversed())
                .limit(Math.max(1, topN))
                .toList();
    }

    public List<CampaignHealth> highAcosCampaigns(String storeName, LocalDate startDate, LocalDate endDate, BigDecimal thresholdPercent) {
        Long storeId = resolveScopedStoreId(storeName);
        Map<Long, AdCampaign> campaigns = campaignRepository.findAll().stream()
                .collect(Collectors.toMap(AdCampaign::getId, Function.identity()));
        return adRows(storeId, startDate, endDate).stream()
                .collect(Collectors.groupingBy(AdDailyReport::getCampaignId))
                .entrySet().stream()
                .map(entry -> {
                    BigDecimal spend = entry.getValue().stream().map(AdDailyReport::getSpend).reduce(BigDecimal.ZERO, BigDecimal::add);
                    BigDecimal sales = entry.getValue().stream().map(AdDailyReport::getSalesAmount).reduce(BigDecimal.ZERO, BigDecimal::add);
                    BigDecimal acos = percent(spend, sales);
                    BigDecimal roas = sales.compareTo(BigDecimal.ZERO) == 0
                            ? BigDecimal.ZERO
                            : sales.divide(spend.max(BigDecimal.ONE), 2, RoundingMode.HALF_UP);
                    AdCampaign c = campaigns.get(entry.getKey());
                    return new CampaignHealth(entry.getKey(), c == null ? "Unknown Campaign" : c.getCampaignName(),
                            c == null ? "Unknown" : c.getChannel(), spend, sales, acos, roas);
                })
                .filter(row -> row.acos().compareTo(thresholdPercent) >= 0)
                .sorted(Comparator.comparing(CampaignHealth::acos).reversed())
                .toList();
    }

    public ReviewInsight reviewInsight(String storeName, int days) {
        Long storeId = resolveScopedStoreId(storeName);
        LocalDate since = LocalDate.now().minusDays(Math.max(7, days));
        List<ProductReview> reviews = storeId == null
                ? reviewRepository.findByRatingLessThanEqualAndReviewDateAfter(3, since)
                : reviewRepository.findByStoreIdAndRatingLessThanEqualAndReviewDateAfter(storeId, 3, since);
        Map<String, Long> themes = new LinkedHashMap<>();
        themes.put("物流/时效", countTheme(reviews, "delay", "late", "shipping", "logistics", "slow", "delivery"));
        themes.put("质量/做工", countTheme(reviews, "quality", "broken", "damaged", "defect", "cheap"));
        themes.put("尺寸/适配", countTheme(reviews, "size", "fit", "small", "large", "compatible"));
        themes.put("说明/预期", countTheme(reviews, "description", "picture", "different", "misleading"));
        List<String> samples = reviews.stream().limit(5).map(ProductReview::getContent).toList();
        return new ReviewInsight(storeId, storeName(storeId), since, reviews.size(), themes, samples);
    }

    public Optional<SkuProduct> findSku(String skuCode) {
        if (skuCode == null || skuCode.isBlank()) {
            return Optional.empty();
        }
        return skuProductRepository.findBySkuCodeIgnoreCase(skuCode.trim());
    }

    private List<RefundRecord> refundRows(Long storeId, LocalDate startDate, LocalDate endDate) {
        return storeId == null
                ? refundRepository.findByRefundDateBetween(startDate, endDate)
                : refundRepository.findByStoreIdAndRefundDateBetween(storeId, startDate, endDate);
    }

    private List<AdDailyReport> adRows(Long storeId, LocalDate startDate, LocalDate endDate) {
        return storeId == null
                ? adReportRepository.findByReportDateBetween(startDate, endDate)
                : adReportRepository.findByStoreIdAndReportDateBetween(storeId, startDate, endDate);
    }

    private Long resolveScopedStoreId(String storeName) {
        UserContext.UserInfo user = UserContext.get();
        Long requested = (storeName == null || storeName.isBlank())
                ? null
                : storeRepository.findByNameContainingIgnoreCase(storeName.trim()).map(Store::getId).orElse(null);
        if (user == null || user.isDirector()) {
            return requested;
        }
        return user.storeId();
    }

    private String storeName(Long storeId) {
        if (storeId == null) {
            return "全部店铺";
        }
        return storeRepository.findById(storeId).map(Store::getName).orElse("未知店铺");
    }

    private long countTheme(List<ProductReview> reviews, String... keywords) {
        return reviews.stream()
                .filter(review -> {
                    String text = review.getContent().toLowerCase(Locale.ROOT);
                    return Arrays.stream(keywords).anyMatch(text::contains);
                })
                .count();
    }

    private BigDecimal percent(BigDecimal numerator, BigDecimal denominator) {
        if (denominator == null || denominator.compareTo(BigDecimal.ZERO) == 0) {
            return BigDecimal.ZERO;
        }
        return numerator.multiply(BigDecimal.valueOf(100)).divide(denominator, 2, RoundingMode.HALF_UP);
    }

    private Object[] summaryRow(Long storeId, LocalDate startDate, LocalDate endDate) {
        Object[] row = orderRepository.summarize(storeId, startDate, endDate);
        return row.length == 1 && row[0] instanceof Object[] nested ? nested : row;
    }

    private BigDecimal decimal(Object value) {
        if (value instanceof BigDecimal bd) {
            return bd;
        }
        if (value instanceof Number number) {
            return BigDecimal.valueOf(number.doubleValue()).setScale(2, RoundingMode.HALF_UP);
        }
        return BigDecimal.ZERO;
    }

    private Number number(Object value) {
        return value instanceof Number n ? n : 0;
    }

    public record BusinessSummary(Long storeId, String storeName, LocalDate startDate, LocalDate endDate,
                                  BigDecimal netSales, BigDecimal profit, BigDecimal profitRate,
                                  BigDecimal averageOrderProfit, BigDecimal refundAmount,
                                  BigDecimal refundRate, long units, long orders) {}

    public record MonthlyTrend(String month, BigDecimal netSales, BigDecimal profit) {}

    public record StoreComparison(Long storeId, String storeName, BigDecimal netSales,
                                  BigDecimal profit, BigDecimal profitRate) {}

    public record SkuRefundRisk(Long skuId, String skuCode, String title, long refunds, long units,
                                BigDecimal refundRate, BigDecimal refundAmount) {}

    public record CampaignHealth(Long campaignId, String campaignName, String channel,
                                 BigDecimal spend, BigDecimal sales, BigDecimal acos, BigDecimal roas) {}

    public record ReviewInsight(Long storeId, String storeName, LocalDate since, int negativeReviewCount,
                                Map<String, Long> themes, List<String> samples) {}
}
