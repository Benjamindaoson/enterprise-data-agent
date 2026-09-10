package com.jichi.salesAgent.repository;

import com.jichi.salesAgent.entity.OperatorUser;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OperatorUserRepository extends JpaRepository<OperatorUser, Long> {
}
