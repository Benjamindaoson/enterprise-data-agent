package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "cb_ad_campaign")
@Getter
@Setter
@NoArgsConstructor
public class AdCampaign {

    @Id
    private Long id;

    @Column(name = "store_id", nullable = false)
    private Long storeId;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    @Column(name = "campaign_name", nullable = false, length = 120)
    private String campaignName;

    @Column(nullable = false, length = 40)
    private String channel;

    @Column(nullable = false, length = 30)
    private String status;
}
