from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
    # Fernet key encrypting Account.session_json at rest (audit C2). Generate:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    session_encryption_key: str

    # CORS — tighten in production. Kept as a raw str (not list[str]) so a plain
    # env value like `https://app.com` doesn't crash startup: pydantic-settings
    # would otherwise demand strict JSON for a complex type. Parsed by
    # `cors_origins_list`, which accepts JSON or a comma-separated list.
    cors_origins: str = "http://localhost:3000"

    # Scraper
    celery_workers: int = 2
    ig_request_delay_min: float = 1.0
    ig_request_delay_max: float = 3.0
    ig_max_requests_per_hour: int = 200
    ig_cooldown_minutes: int = 30
    # Stop handing out an account this many requests short of the hourly cap
    # (anti-ban rule 2's "stop at 180 for margin" — was hardcoded as `- 20`
    # in both account_pool.py and _sync_helpers.py; audit L5).
    ig_rate_limit_margin: int = 20
    # Consecutive ChallengeRequired/FeedbackRequired hits before an account is
    # permanently banned instead of re-cooling-down forever (audit AUDIT-2.md H3).
    ig_challenge_streak_limit: int = 3

    # App
    log_level: str = "INFO"
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw:
            return []
        if raw.startswith("["):
            import json

            try:
                return [str(o) for o in json.loads(raw)]
            except json.JSONDecodeError:
                pass
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
