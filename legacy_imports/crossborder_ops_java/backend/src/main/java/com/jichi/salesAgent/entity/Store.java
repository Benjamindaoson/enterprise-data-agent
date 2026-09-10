package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "cb_store")
@Getter
@Setter
@NoArgsConstructor
public class Store {

    @Id
    private Long id;

    @Column(nullable = false, length = 80)
    private String name;

    @Column(nullable = false, length = 40)
    private String platform;

    @Column(nullable = false, length = 40)
    private String marketplace;

    @Column(nullable = false, length = 10)
    private String currency;

    @Column(name = "manager_operator_id")
    private Long managerOperatorId;
}
