"""
Extract contact information from Instagram bio text.
All data extracted here is publicly visible on Instagram profiles.
"""

import re

# Email: RFC 5321 simplified
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Brazilian phone (supports +55, DDD, 8/9 digit numbers)
_PHONE_RE = re.compile(
    r"(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}[\s\-]?\d{4}|\d{4}[\s\-]?\d{4})"
)

# URLs (http/https)
_URL_RE = re.compile(
    r"https?://[^\s\)\]\>\"\']+",
    re.IGNORECASE,
)

# Common IG bio link services to skip (not real websites)
_SKIP_DOMAINS = {"linktr.ee", "linktree.com", "instagram.com", "wa.me", "t.me"}


def extract_email(bio: str) -> str | None:
    """Extract first valid email from bio text."""
    if not bio:
        return None
    match = _EMAIL_RE.search(bio)
    if match:
        email = match.group(0).lower().strip(".")
        # Basic sanity: has TLD, not too long
        if len(email) <= 320 and "." in email.split("@")[-1]:
            return email
    return None


def extract_phone(bio: str) -> str | None:
    """Extract first phone number from bio text."""
    if not bio:
        return None
    match = _PHONE_RE.search(bio)
    if match:
        # Normalize: keep only digits
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if 8 <= len(digits) <= 13:
            return digits
    return None


def extract_website(bio: str, existing_website: str | None = None) -> str | None:
    """
    Extract website URL. Prefers the profile's `external_url` field
    over bio parsing. Filters out known social link aggregators.
    """
    if existing_website:
        domain = _get_domain(existing_website)
        if domain and domain not in _SKIP_DOMAINS:
            return existing_website

    if not bio:
        return None

    for match in _URL_RE.finditer(bio):
        url = match.group(0).rstrip(".,;")
        domain = _get_domain(url)
        if domain and domain not in _SKIP_DOMAINS:
            return url

    return None


def _get_domain(url: str) -> str | None:
    """Extract base domain from URL."""
    try:
        # Simple extraction without full URL parsing lib
        without_scheme = url.split("://", 1)[-1]
        domain = without_scheme.split("/")[0].lower()
        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if "." in domain else None
    except Exception:
        return None
