from __future__ import annotations

import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name) or default


DB_URL = env("DB_URL", "mysql+pymysql://root:@127.0.0.1:3306/crossborder_ops?charset=utf8mb4")
LLM_BASE_URL = env("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
LLM_API_KEY = env("LLM_API_KEY")
LLM_MODEL = env("LLM_MODEL", "deepseek-chat")
APP_AUTH_ENABLED = env("APP_AUTH_ENABLED", "false").lower() == "true"
