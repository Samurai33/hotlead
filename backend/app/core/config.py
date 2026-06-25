from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8",
        case_sensitive=False, extra="ignore",
    )

    # Database
    database_url: str
    postgres_user: str = "hotlead"
    postgres_password: str
    postgres_db: str = "hotlead"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Security
    secret_key: str
    api_key: str

    # CORS — tighten in production
    cors_origins: list[str] = ["http://localhost:3000"]

    # Scraper
    celery_workers: int = 2
    ig_request_delay_min: float = 1.0
    ig_request_delay_max: float = 3.0
    ig_max_requests_per_hour: int = 200
    ig_cooldown_minutes: int = 30

    # App
    log_level: str = "INFO"
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
