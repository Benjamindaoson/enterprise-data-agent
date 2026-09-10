package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.SkuProduct;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface SkuProductRepository extends JpaRepository<SkuProduct, Long> {
    List<SkuProduct> findByStoreId(Long storeId);
    Optional<SkuProduct> findBySkuCodeIgnoreCase(String skuCode);
}
