"""
Instagram client wrapper — simulates Android IG app.
Anti-ban: mandatory random delay, session-only auth, batch pagination.
"""
import json, logging, random, time
from typing import Generator
from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired, LoginRequired, RateLimitError, UserNotFound,
    PleaseWaitFewMinutes,
)
from app.core.config import get_settings
from app.scraper.extractor import extract_email, extract_phone, extract_website

logger = logging.getLogger(__name__)
settings = get_settings()

class RateLimitExceeded(Exception): pass
class AccountChallenged(Exception): pass
class ProfileNotFound(Exception): pass


class IGClient:
    """Wrapper around instagrapi.Client with anti-ban controls."""

    def __init__(self, username: str, session_json: str | None, proxy_url: str | None = None):
        self.username = username
        self._cl = Client()
        if proxy_url:
            self._cl.set_proxy(proxy_url)
        if not session_json:
            raise ValueError(f"No session for @{username}. Use add_account.py first.")
        self._cl.load_settings(json.loads(session_json))
        logger.info(f"[{username}] Session loaded")

    def get_user_id(self, username: str) -> str:
        self._delay()
        try:
            return self._cl.user_id_from_username(username)
        except UserNotFound:
            raise ProfileNotFound(f"@{username} not found or is private")
        except (RateLimitError, PleaseWaitFewMinutes):
            raise RateLimitExceeded(f"Rate limit on @{self.username}")
        except (ChallengeRequired, LoginRequired):
            raise AccountChallenged(f"Challenge on @{self.username}")

    def iter_followers(self, username: str, max_count: int = 0) -> Generator[dict, None, None]:
        """Yield follower dicts. max_count=0 = unlimited."""
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
            except (RateLimitError, PleaseWaitFewMinutes):
                raise RateLimitExceeded(f"Rate limit on @{self.username}")
            except (ChallengeRequired, LoginRequired):
                raise AccountChallenged(f"Challenge on @{self.username}")
            for user in batch:
                yield self._normalize(user)
                scraped += 1
                if max_count and scraped >= max_count:
                    return
            if not next_cursor:
                break

    def iter_following(self, username: str, max_count: int = 0) -> Generator[dict, None, None]:
        """Yield following dicts."""
        user_id = self.get_user_id(username)
        next_cursor = None
        scraped = 0
        while True:
            if max_count and scraped >= max_count:
                break
            self._delay()
            try:
                batch, next_cursor = self._cl.user_following_v1_chunk(
                    user_id, max_amount=50, next_cursor=next_cursor
                )
            except (RateLimitError, PleaseWaitFewMinutes):
                raise RateLimitExceeded(f"Rate limit on @{self.username}")
            except (ChallengeRequired, LoginRequired):
                raise AccountChallenged(f"Challenge on @{self.username}")
            for user in batch:
                yield self._normalize(user)
                scraped += 1
                if max_count and scraped >= max_count:
                    return
            if not next_cursor:
                break

    def iter_commenters(self, post_url: str, max_count: int = 0) -> Generator[dict, None, None]:
        """Yield unique users who commented on a post. Deduplicates by user PK."""
        self._delay()
        try:
            media_pk = self._cl.media_pk_from_url(post_url)
        except (RateLimitError, PleaseWaitFewMinutes):
            raise RateLimitExceeded(f"Rate limit on @{self.username}")
        except (ChallengeRequired, LoginRequired):
            raise AccountChallenged(f"Challenge on @{self.username}")
        except Exception as exc:
            raise ProfileNotFound(f"Cannot resolve post URL: {exc}")

        seen_pks: set[str] = set()
        fetch_amount = max_count if max_count else 500

        self._delay()
        try:
            comments = self._cl.media_comments(media_pk, amount=fetch_amount)
        except (RateLimitError, PleaseWaitFewMinutes):
            raise RateLimitExceeded(f"Rate limit on @{self.username}")
        except (ChallengeRequired, LoginRequired):
            raise AccountChallenged(f"Challenge on @{self.username}")

        for comment in comments:
            pk = str(comment.user.pk)
            if pk in seen_pks:
                continue
            seen_pks.add(pk)
            yield self._normalize_short(comment.user)
            if max_count and len(seen_pks) >= max_count:
                return

    def get_updated_session(self) -> str:
        return json.dumps(self._cl.get_settings())

    def _delay(self):
        """Mandatory random delay — NEVER skip."""
        time.sleep(random.uniform(settings.ig_request_delay_min, settings.ig_request_delay_max))

    @staticmethod
    def _normalize(user) -> dict:
        bio = getattr(user, "biography", "") or ""
        website = getattr(user, "external_url", None)
        return {
            "username":    user.username,
            "full_name":   getattr(user, "full_name", None),
            "ig_pk":       str(user.pk),
            "biography":   bio,
            "followers":   getattr(user, "follower_count", 0),
            "following":   getattr(user, "following_count", 0),
            "is_business": getattr(user, "is_business", False),
            "is_private":  getattr(user, "is_private", False),
            "is_verified": getattr(user, "is_verified", False),
            "email":       extract_email(bio),
            "phone":       extract_phone(bio),
            "website":     extract_website(bio, website),
        }

    @staticmethod
    def _normalize_short(user) -> dict:
        """Normalize a UserShort (from comments) — no bio/followers available."""
        return {
            "username":    user.username,
            "full_name":   getattr(user, "full_name", None),
            "ig_pk":       str(user.pk),
            "biography":   None,
            "followers":   0,
            "following":   0,
            "is_business": False,
            "is_private":  getattr(user, "is_private", False),
            "is_verified": getattr(user, "is_verified", False),
            "email":       None,
            "phone":       None,
            "website":     None,
        }
