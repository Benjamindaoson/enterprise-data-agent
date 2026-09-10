package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;

@Entity
@Table(name = "cb_sku")
@Getter
@Setter
@NoArgsConstructor
public class SkuProduct {

    @Id
    private Long id;

    @Column(name = "store_id", nullable = false)
    private Long storeId;

    @Column(name = "sku_code", nullable = false, length = 60)
    private String skuCode;

    @Column(nullable = false, length = 160)
    private String title;

    @Column(nullable = false, length = 60)
    private String category;

    @Column(name = "target_marketplace", nullable = false, length = 40)
    private String targetMarketplace;

    @Column(name = "unit_cost", nullable = false, precision = 12, scale = 2)
    private BigDecimal unitCost;

    @Column(nullable = false, length = 30)
    private String status;
}
