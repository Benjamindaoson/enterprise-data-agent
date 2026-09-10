package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.AdCampaign;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AdCampaignRepository extends JpaRepository<AdCampaign, Long> {
    List<AdCampaign> findByStoreId(Long storeId);
}
