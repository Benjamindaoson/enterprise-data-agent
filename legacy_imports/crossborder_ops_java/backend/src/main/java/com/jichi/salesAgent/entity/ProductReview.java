package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;

@Entity
@Table(name = "cb_review")
@Getter
@Setter
@NoArgsConstructor
public class ProductReview {

    @Id
    private Long id;

    @Column(name = "store_id", nullable = false)
    private Long storeId;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    @Column(nullable = false)
    private Integer rating;

    @Column(nullable = false, length = 600)
    private String content;

    @Column(nullable = false, length = 20)
    private String locale;

    @Column(name = "review_date", nullable = false)
    private LocalDate reviewDate;
}
