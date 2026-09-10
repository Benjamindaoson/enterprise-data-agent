package com.jichi.salesAgent.config;

import cn.dev33.satoken.interceptor.SaInterceptor;
import cn.dev33.satoken.session.SaSession;
import cn.dev33.satoken.stp.StpUtil;
import com.jichi.salesAgent.security.UserContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@Slf4j
public class WebMvcConfig implements WebMvcConfigurer {

    @Value("${app.auth.enabled:false}")
    private boolean authEnabled;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        if (!authEnabled) {
            log.warn("Auth check is disabled. Use this mode only for local classroom demos.");
            registry.addInterceptor(cleanupInterceptor()).addPathPatterns("/**");
            return;
        }

        registry.addInterceptor(new SaInterceptor(handle -> StpUtil.checkLogin()))
                .addPathPatterns("/**")
                .excludePathPatterns("/auth/login", "/actuator/**", "/static/**");

        registry.addInterceptor(new HandlerInterceptor() {
            @Override
            public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
                if (StpUtil.isLogin()) {
                    Long userId = StpUtil.getLoginIdAsLong();
                    SaSession session = StpUtil.getSession();
                    String username = (String) session.get("username");
                    String role = (String) session.get("role");
                    Long storeId = session.get("storeId") instanceof Number n ? n.longValue() : null;
                    Long operatorId = session.get("operatorId") instanceof Number n ? n.longValue() : null;
                    UserContext.set(new UserContext.UserInfo(userId, username, role, storeId, operatorId));
                    log.debug("operator authenticated userId={}, role={}, storeId={}", userId, role, storeId);
                }
                return true;
            }

            @Override
            public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
                UserContext.clear();
            }
        }).addPathPatterns("/**");
    }

    private HandlerInterceptor cleanupInterceptor() {
        return new HandlerInterceptor() {
            @Override
            public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
                UserContext.clear();
            }
        };
    }
}
