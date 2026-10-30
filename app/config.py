"""
Centralized application configuration.

All settings are sourced from environment variables so the same container
image can be promoted across dev / staging / prod without rebuilding,
following the 12-factor app methodology. In Kubernetes these are injected
via ConfigMaps (non-sensitive) and Secrets (sensitive).
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "taskapi"
    app_env: str = "development"
    log_level: str = "info"
    log_format: str = "json"  # json or text

    # Database settings
    database_url: str = "sqlite:///./taskapi.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # Redis settings (optional resilience layer)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_ttl_seconds: int = 30
    redis_connect_timeout: float = 1.0
    cache_enabled: bool = True

    # Security & Networking
    cors_origins: list[str] | str = ["*"]
    allowed_hosts: list[str] | str = ["*"]
    enable_security_headers: bool = True
    enable_gzip: bool = True
    gzip_min_size: int = 500
    auth_enabled: bool = False
    api_key: str | None = None

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # Observability & OpenTelemetry
    otel_enabled: bool = False
    otel_service_name: str = "taskapi"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # Pagination Defaults
    default_page_size: int = 20
    max_page_size: int = 100

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def assemble_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v if isinstance(v, list) else [v]


settings = Settings()
