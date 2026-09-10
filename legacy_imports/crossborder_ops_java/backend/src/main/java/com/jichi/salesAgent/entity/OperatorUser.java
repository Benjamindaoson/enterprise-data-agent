package com.jichi.salesAgent.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "cb_operator")
@Getter
@Setter
@NoArgsConstructor
public class OperatorUser {

    @Id
    private Long id;

    @Column(nullable = false, length = 60)
    private String name;

    @Column(nullable = false, length = 40)
    private String role;

    @Column(name = "store_id")
    private Long storeId;

    @Column(length = 120)
    private String email;
}
