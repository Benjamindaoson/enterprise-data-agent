package com.jichi.salesAgent.controller;

import cn.dev33.satoken.stp.StpUtil;
import com.jichi.salesAgent.entity.OperatorUser;
import com.jichi.salesAgent.repository.OperatorUserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final OperatorUserRepository operatorRepository;

    record LoginRequest(Long operatorId) {}

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request) {
        if (request.operatorId() == null) {
            return ResponseEntity.badRequest().body("请输入运营账号 ID");
        }

        OperatorUser operator = operatorRepository.findById(request.operatorId()).orElse(null);
        if (operator == null) {
            return ResponseEntity.badRequest().body("运营账号不存在");
        }

        StpUtil.login(operator.getId());
        var session = StpUtil.getSession()
                .set("username", operator.getName())
                .set("role", operator.getRole())
                .set("operatorId", operator.getId());
        if (operator.getStoreId() != null) {
            session.set("storeId", operator.getStoreId());
        }

        return ResponseEntity.ok(Map.of(
                "token", StpUtil.getTokenValue(),
                "username", operator.getName(),
                "role", operator.getRole(),
                "operatorId", operator.getId(),
                "storeId", operator.getStoreId() == null ? "" : operator.getStoreId()
        ));
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout() {
        StpUtil.logout();
        return ResponseEntity.ok(Map.of("message", "已退出登录"));
    }
}
