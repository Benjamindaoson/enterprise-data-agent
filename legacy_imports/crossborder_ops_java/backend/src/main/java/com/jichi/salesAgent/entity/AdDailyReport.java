package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "cb_ad_daily_report")
@Getter
@Setter
@NoArgsConstructor
public class AdDailyReport {

    @Id
    private Long id;

    @Column(name = "campaign_id", nullable = false)
    private Long campaignId;

    @Column(name = "store_id", nullable = false)
    private Long storeId;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    @Column(name = "report_date", nullable = false)
    private LocalDate reportDate;

    @Column(nullable = false, precision = 14, scale = 2)
    private BigDecimal spend;

    @Column(name = "sales_amount", nullable = false, precision = 14, scale = 2)
    private BigDecimal salesAmount;

    @Column(nullable = false)
    private Integer clicks;

    @Column(nullable = false)
    private Integer orders;
}
