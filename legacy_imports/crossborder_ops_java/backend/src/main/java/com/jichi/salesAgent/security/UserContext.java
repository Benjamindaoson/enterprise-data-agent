package com.jichi.salesAgent.security;

public class UserContext {

    private static final ThreadLocal<UserInfo> HOLDER = new ThreadLocal<>();

    public record UserInfo(Long userId, String username, String role, Long storeId, Long operatorId) {
        public boolean isDirector() {
            return "OPERATIONS_DIRECTOR".equals(role);
        }

        public boolean isStoreManager() {
            return "STORE_MANAGER".equals(role);
        }

        public boolean isOperator() {
            return "OPERATOR".equals(role);
        }

    }

    public static void set(UserInfo info) {
        HOLDER.set(info);
    }

    public static UserInfo get() {
        return HOLDER.get();
    }

    public static void clear() {
        HOLDER.remove();
    }

    public static boolean isDirector() {
        UserInfo u = get();
        return u != null && u.isDirector();
    }

    public static boolean isStoreManager() {
        UserInfo u = get();
        return u != null && u.isStoreManager();
    }
}
