package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.AdDailyReport;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;

public interface AdDailyReportRepository extends JpaRepository<AdDailyReport, Long> {
    List<AdDailyReport> findByReportDateBetween(LocalDate startDate, LocalDate endDate);
    List<AdDailyReport> findByStoreIdAndReportDateBetween(Long storeId, LocalDate startDate, LocalDate endDate);
}
