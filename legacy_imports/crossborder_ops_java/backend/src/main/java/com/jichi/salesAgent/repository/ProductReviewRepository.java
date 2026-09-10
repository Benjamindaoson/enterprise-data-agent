package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.ProductReview;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;

public interface ProductReviewRepository extends JpaRepository<ProductReview, Long> {
    List<ProductReview> findByStoreIdAndRatingLessThanEqualAndReviewDateAfter(Long storeId, Integer rating, LocalDate reviewDate);
    List<ProductReview> findByRatingLessThanEqualAndReviewDateAfter(Integer rating, LocalDate reviewDate);
}
