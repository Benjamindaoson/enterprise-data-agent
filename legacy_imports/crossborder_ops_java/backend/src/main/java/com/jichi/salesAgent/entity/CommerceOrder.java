package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "cb_order")
@Getter
@Setter
@NoArgsConstructor
public class CommerceOrder {

    @Id
    private Long id;

    @Column(name = "order_no", nullable = false, length = 60)
    private String orderNo;

    @Column(name = "store_id", nullable = false)
    private Long storeId;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    @Column(nullable = false, length = 40)
    private String country;

    @Column(nullable = false)
    private Integer quantity;

    @Column(name = "gross_amount", nullable = false, precision = 14, scale = 2)
    private BigDecimal grossAmount;

    @Column(name = "net_amount", nullable = false, precision = 14, scale = 2)
    private BigDecimal netAmount;

    @Column(name = "cost_amount", nullable = false, precision = 14, scale = 2)
    private BigDecimal costAmount;

    @Column(name = "profit_amount", nullable = false, precision = 14, scale = 2)
    private BigDecimal profitAmount;

    @Column(nullable = false, length = 30)
    private String status;

    @Column(name = "order_date", nullable = false)
    private LocalDate orderDate;
}
