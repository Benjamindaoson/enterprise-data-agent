package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.ProductListing;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ProductListingRepository extends JpaRepository<ProductListing, Long> {
    Optional<ProductListing> findFirstBySkuIdAndMarketplaceIgnoreCase(Long skuId, String marketplace);
}
