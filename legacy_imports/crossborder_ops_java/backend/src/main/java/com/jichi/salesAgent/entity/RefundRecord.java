package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "cb_refund")
@Getter
@Setter
@NoArgsConstructor
public class RefundRecord {

    @Id
    private Long id;

    @Column(name = "order_id", nullable = false)
    private Long orderId;

    @Column(name = "store_id", nullable = false)
    private Long storeId;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    @Column(nullable = false, length = 120)
    private String reason;

    @Column(name = "refund_amount", nullable = false, precision = 14, scale = 2)
    private BigDecimal refundAmount;

    @Column(name = "refund_date", nullable = false)
    private LocalDate refundDate;
}
