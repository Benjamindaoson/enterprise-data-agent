package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.CommerceOrder;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public interface CommerceOrderRepository extends JpaRepository<CommerceOrder, Long> {

    List<CommerceOrder> findByOrderDateBetween(LocalDate startDate, LocalDate endDate);

    List<CommerceOrder> findByStoreIdAndOrderDateBetween(Long storeId, LocalDate startDate, LocalDate endDate);

    @Query("""
            select coalesce(sum(o.netAmount), 0), coalesce(sum(o.profitAmount), 0), coalesce(sum(o.quantity), 0), count(o)
            from CommerceOrder o
            where o.orderDate between :startDate and :endDate
              and (:storeId is null or o.storeId = :storeId)
            """)
    Object[] summarize(@Param("storeId") Long storeId,
                       @Param("startDate") LocalDate startDate,
                       @Param("endDate") LocalDate endDate);

    @Query("""
            select o.skuId, coalesce(sum(o.quantity), 0), coalesce(sum(o.netAmount), 0), coalesce(sum(o.profitAmount), 0), count(o)
            from CommerceOrder o
            where o.orderDate between :startDate and :endDate
              and (:storeId is null or o.storeId = :storeId)
            group by o.skuId
            """)
    List<Object[]> summarizeBySku(@Param("storeId") Long storeId,
                                  @Param("startDate") LocalDate startDate,
                                  @Param("endDate") LocalDate endDate);

    @Query(value = """
            select date_format(o.order_date, '%Y-%m') as ym,
                   coalesce(sum(o.net_amount), 0) as net_amount,
                   coalesce(sum(o.profit_amount), 0) as profit_amount
            from cb_order o
            where o.order_date between :startDate and :endDate
              and (:storeId is null or o.store_id = :storeId)
            group by date_format(o.order_date, '%Y-%m')
            order by ym
            """, nativeQuery = true)
    List<Object[]> monthlyTrend(@Param("storeId") Long storeId,
                                @Param("startDate") LocalDate startDate,
                                @Param("endDate") LocalDate endDate);

    default BigDecimal profitRate(BigDecimal netAmount, BigDecimal profitAmount) {
        if (netAmount == null || BigDecimal.ZERO.compareTo(netAmount) == 0) {
            return BigDecimal.ZERO;
        }
        return profitAmount.multiply(BigDecimal.valueOf(100)).divide(netAmount, 2, java.math.RoundingMode.HALF_UP);
    }
}
