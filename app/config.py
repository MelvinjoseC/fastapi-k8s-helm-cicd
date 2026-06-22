"""
Centralized application configuration.

All settings are sourced from environment variables so the same container
image can be promoted across dev / staging / prod without rebuilding,
following the 12-factor app methodology. In Kubernetes these are injected
via ConfigMaps (non-sensitive) and Secrets (sensitive).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "taskapi"
    app_env: str = "development"
    log_level: str = "info"

    # Falls back to local SQLite so the app and tests run with zero
    # external dependencies. In Kubernetes this is overridden by a
    # Secret pointing at the Postgres StatefulSet/managed DB.
    database_url: str = "sqlite:///./taskapi.db"

    # Redis is treated as an optional accelerator, not a hard dependency.
    # If it's unreachable the app degrades gracefully instead of crashing.
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_ttl_seconds: int = 30

    cache_enabled: bool = True


settings = Settings()
