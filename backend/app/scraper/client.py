"""
Instagram client wrapper around instagrapi.
Simulates the Instagram Android app to avoid detection.

ANTI-BAN RULES (never bypass):
  1. Always delay between requests (randomized 1–3s)
  2. Max 200 requests/hour per account (tracked in Redis)
  3. Save session JSON after every login
  4. Never store Instagram passwords
"""

import json
import logging
import random
import time
from typing import Generator

from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    RateLimitError,
    UserNotFound,
)

from app.core.config import get_settings
from app.scraper.extractor import extract_email, extract_phone, extract_website

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitExceeded(Exception):
    """Raised when per-account request limit is hit."""


class AccountChallenged(Exception):
    """Raised when Instagram issues a challenge (human verification)."""


class IGClient:
    """
    Thin wrapper around instagrapi.Client.
    Handles delays, session management, and error translation.
    """

    def __init__(
        self, username: str, session_json: str | None, proxy_url: str | None = None
    ):
        self.username = username
        self._cl = Client()

        if proxy_url:
            self._cl.set_proxy(proxy_url)

        if session_json:
            self._cl.load_settings(json.loads(session_json))
            logger.info(f"[{username}] Loaded existing session")
        else:
            raise ValueError(
                f"No session for account @{username}. Login first via add_account script."
            )

    # ─── Public interface ─────────────────────────────────────

    def get_user_id(self, username: str) -> str:
        self._delay()
        try:
            return self._cl.user_id_from_username(username)
        except UserNotFound:
            raise ValueError(f"Instagram user @{username} not found or is private")

    def iter_followers(
        self, username: str, max_count: int = 0
    ) -> Generator[dict, None, None]:
        """
        Yields follower data dicts. Handles pagination internally.
        Use max_count=0 for unlimited.
        """
        user_id = self.get_user_id(username)
        next_cursor = None
        scraped = 0

        while True:
            if max_count and scraped >= max_count:
                break

            self._delay()

            try:
                batch, next_cursor = self._cl.user_followers_v1_chunk(
                    user_id, max_amount=50, next_cursor=next_cursor
                )
            except RateLimitError:
                raise RateLimitExceeded(f"Rate limit hit for @{self.username}")
            except ChallengeRequired:
                raise AccountChallenged(f"Challenge required for @{self.username}")
            except LoginRequired:
                raise AccountChallenged(f"Session expired for @{self.username}")

            for user in batch:
                yield self._normalize_user(user)
                scraped += 1
                if max_count and scraped >= max_count:
                    return

            if not next_cursor:
                break

    def get_updated_session(self) -> str:
        """Return updated session JSON (call after operations to persist fresh cookies)."""
        return json.dumps(self._cl.get_settings())

    # ─── Private helpers ──────────────────────────────────────

    def _delay(self):
        """Mandatory delay between requests. Never skip this."""
        delay = random.uniform(
            settings.ig_request_delay_min,
            settings.ig_request_delay_max,
        )
        time.sleep(delay)

    @staticmethod
    def _normalize_user(user) -> dict:
        """Convert instagrapi UserShort/User to our prospect dict."""
        bio = getattr(user, "biography", "") or ""
        website = getattr(user, "external_url", None)

        return {
            "username": user.username,
            "full_name": getattr(user, "full_name", None),
            "ig_pk": str(user.pk),
            "biography": bio,
            "followers": getattr(user, "follower_count", 0),
            "following": getattr(user, "following_count", 0),
            "is_business": getattr(user, "is_business", False),
            "is_private": getattr(user, "is_private", False),
            "is_verified": getattr(user, "is_verified", False),
            # Extracted contact
            "email": extract_email(bio),
            "phone": extract_phone(bio),
            "website": extract_website(bio, website),
        }
