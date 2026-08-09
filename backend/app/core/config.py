from functools import lru_cache

from pydantic import SecretStr
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
    postgres_password: SecretStr
    postgres_db: str = "hotlead"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Security. SecretStr (audit AUDIT-2.md M8) masks these in repr()/tracebacks/
    # accidental logging -- callers need .get_secret_value() to use the real value.
    secret_key: SecretStr
    api_key: SecretStr
    # Fernet key encrypting Account.session_json at rest (audit C2). Generate:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    session_encryption_key: SecretStr

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
    # Checkout lease TTL: renewed on every real IG request, so a live job never
    # loses it; only needs margin over ig_request_delay_max, not the whole job
    # duration. A crashed worker's account self-frees once this passes instead
    # of sticking to it forever (audit AUDIT-2.md H4).
    ig_account_lease_minutes: int = 15

    # Per-IP fixed-window cap on POST /jobs and POST /accounts (audit
    # AUDIT-2.md H1) -- prevents a leaked key/scripting mistake from
    # flooding job creation and mass-triggering cooldowns pool-wide.
    api_rate_limit_per_minute: int = 20

    # Per-request socket timeout for instagrapi calls -- without this, a
    # dead proxy socket hangs the underlying request forever (audit
    # AUDIT-2.md M7's "one wedged network call parks a worker forever").
    ig_request_timeout_seconds: int = 30
    # Celery task-level safety net on top of the per-request timeout above --
    # generous enough not to kill a legitimately large scrape (thousands of
    # followers), but finite so a wedged worker eventually surfaces instead
    # of parking that worker_prefetch_multiplier=1 slot forever with no
    # operator signal (audit AUDIT-2.md M7).
    celery_task_soft_time_limit_seconds: int = 7200
    celery_task_time_limit_seconds: int = 7500

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
