package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "cb_listing")
@Getter
@Setter
@NoArgsConstructor
public class ProductListing {

    @Id
    private Long id;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    @Column(nullable = false, length = 40)
    private String marketplace;

    @Column(nullable = false, length = 20)
    private String locale;

    @Column(nullable = false, length = 220)
    private String title;

    @Column(nullable = false, length = 1200)
    private String bullets;

    @Column(nullable = false, length = 300)
    private String keywords;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
