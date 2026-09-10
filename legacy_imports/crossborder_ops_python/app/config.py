from __future__ import annotations

from dataclasses import dataclass
import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name) or default


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_list(name: str, default: str = "*") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "crossborder-ops-agent-python"
    environment: str = "local"
    db_url: str = "mysql+pymysql://root:@127.0.0.1:3306/crossborder_ops?charset=utf8mb4"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_enabled: bool = True
    auth_enabled: bool = False
    auth_secret: str = "change-me"
    login_code: str = ""
    access_token_ttl_seconds: int = 3600
    cors_origins: list[str] | None = None
    rate_limit_per_minute: int = 0
    redis_url: str = ""
    otel_enabled: bool = False
    otel_endpoint: str = ""
    identity_provider: str = "local"
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=env("APP_NAME", cls.app_name),
            environment=env("APP_ENV", cls.environment),
            db_url=env("DB_URL", cls.db_url),
            llm_base_url=env("LLM_BASE_URL", cls.llm_base_url).rstrip("/"),
            llm_api_key=env("LLM_API_KEY"),
            llm_model=env("LLM_MODEL", cls.llm_model),
            llm_enabled=env_bool("LLM_ENABLED", True),
            auth_enabled=env_bool("APP_AUTH_ENABLED", False),
            auth_secret=env("APP_AUTH_SECRET", cls.auth_secret),
            login_code=env("APP_LOGIN_CODE"),
            access_token_ttl_seconds=env_int("ACCESS_TOKEN_TTL_SECONDS", cls.access_token_ttl_seconds),
            cors_origins=env_list("CORS_ORIGINS", "*"),
            rate_limit_per_minute=env_int("RATE_LIMIT_PER_MINUTE", 0),
            redis_url=env("REDIS_URL"),
            otel_enabled=env_bool("OTEL_ENABLED", False),
            otel_endpoint=env("OTEL_EXPORTER_OTLP_ENDPOINT"),
            identity_provider=env("IDENTITY_PROVIDER", cls.identity_provider),
            oidc_issuer=env("OIDC_ISSUER"),
            oidc_audience=env("OIDC_AUDIENCE"),
            oidc_jwks_url=env("OIDC_JWKS_URL"),
        )


SETTINGS = Settings.from_env()


DB_URL = SETTINGS.db_url
LLM_BASE_URL = SETTINGS.llm_base_url
LLM_API_KEY = SETTINGS.llm_api_key
LLM_MODEL = SETTINGS.llm_model
APP_AUTH_ENABLED = SETTINGS.auth_enabled
