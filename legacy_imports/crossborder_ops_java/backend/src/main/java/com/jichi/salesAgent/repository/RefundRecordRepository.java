package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.RefundRecord;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;

public interface RefundRecordRepository extends JpaRepository<RefundRecord, Long> {
    List<RefundRecord> findByRefundDateBetween(LocalDate startDate, LocalDate endDate);
    List<RefundRecord> findByStoreIdAndRefundDateBetween(Long storeId, LocalDate startDate, LocalDate endDate);
}
