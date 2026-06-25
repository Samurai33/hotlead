"""Extract contact data from Instagram bio text (publicly visible data only)."""
import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}[\s\-]?\d{4}|\d{4}[\s\-]?\d{4})")
_URL_RE   = re.compile(r"https?://[^\s\)\]\>\"\']+", re.IGNORECASE)
_SKIP     = {"linktr.ee","linktree.com","instagram.com","wa.me","t.me","bio.link","beacons.ai","allmylinks.com"}


def extract_email(bio: str | None) -> str | None:
    if not bio:
        return None
    m = _EMAIL_RE.search(bio)
    if m:
        e = m.group(0).lower().strip(".")
        if len(e) <= 320 and "." in e.split("@")[-1]:
            return e
    return None


def extract_phone(bio: str | None) -> str | None:
    if not bio:
        return None
    m = _PHONE_RE.search(bio)
    if m:
        d = re.sub(r"\D", "", m.group(0))
        if 8 <= len(d) <= 13:
            return d
    return None


def extract_website(bio: str | None, external_url: str | None = None) -> str | None:
    if external_url:
        d = _domain(external_url)
        if d and d not in _SKIP:
            return external_url
    if not bio:
        return None
    for m in _URL_RE.finditer(bio):
        url = m.group(0).rstrip(".,;)")
        d = _domain(url)
        if d and d not in _SKIP:
            return url
    return None


def _domain(url: str) -> str | None:
    try:
        d = url.split("://", 1)[-1].split("/")[0].lower()
        return d[4:] if d.startswith("www.") else (d if "." in d else None)
    except Exception:
        return None
