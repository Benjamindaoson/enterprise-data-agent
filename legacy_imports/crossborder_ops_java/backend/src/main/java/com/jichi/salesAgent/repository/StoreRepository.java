package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.Store;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface StoreRepository extends JpaRepository<Store, Long> {
    Optional<Store> findByNameContainingIgnoreCase(String name);
}
