"""Extract contact data from Instagram bio text (publicly visible data only)."""

import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)

# Deliberate scraper evasion, not an edge case (audit AUDIT-2.md H5): bios that
# want contact but not naive regex matches commonly write "name [at] domain
# [dot] com". Requires the surrounding tokens to already look like
# identifier/domain fragments (no spaces) so this doesn't fire on ordinary
# prose that happens to contain the words "at"/"dot" — only tried as a
# fallback when the plain _EMAIL_RE above finds nothing, and the
# reconstructed candidate still has to pass _EMAIL_RE itself.
_OBFUSCATED_EMAIL_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)"
    r"\s*(?:\[at\]|\(at\)|\{at\}| at )\s*"
    r"([a-zA-Z0-9\-]+(?:\s*(?:\[dot\]|\(dot\)|\{dot\}| dot )\s*[a-zA-Z0-9\-]+)+)",
    re.IGNORECASE,
)
_OBFUSCATED_DOT_RE = re.compile(r"\s*(?:\[dot\]|\(dot\)|\{dot\}| dot )\s*", re.IGNORECASE)

# General international phone matcher (audit H5: the old regex was BR-only,
# silently failing on every other country despite no stated BR-only scope).
# Scans for a run of digits loosely grouped by common phone punctuation
# (space, dot, dash, parens) or glued together, optionally starting with a
# leading "+"/"(" — the 8-15 total-digit bound (E.164's max length) in
# extract_phone below is what actually keeps this from matching arbitrary
# short digit runs in prose (dates, follower counts, etc).
_PHONE_RE = re.compile(r"(?<!\d)[\s.\-(+]{0,2}(?:\d[\s.\-()]{0,2}){7,14}\d(?!\d)")

# Keycap digit emoji (0-9 as keycaps): DIGIT + U+FE0F (variation selector,
# optional) + U+20E3 (combining enclosing keycap) — the documented
# "emoji-separated digits" evasion (audit H5). Normalized back to plain
# digits before phone matching.
_KEYCAP_DIGIT_RE = re.compile("([0-9])️?⃣")

_URL_RE = re.compile(r"https?://[^\s\)\]\>\"\']+", re.IGNORECASE)
_SKIP = {
    "linktr.ee",
    "linktree.com",
    "instagram.com",
    "wa.me",
    "t.me",
    "bio.link",
    "beacons.ai",
    "allmylinks.com",
}


def extract_email(bio: str | None) -> str | None:
    if not bio:
        return None
    m = _EMAIL_RE.search(bio)
    candidate = m.group(0) if m else None
    if candidate is None:
        m2 = _OBFUSCATED_EMAIL_RE.search(bio)
        if m2:
            local, domain_part = m2.group(1), m2.group(2)
            domain = _OBFUSCATED_DOT_RE.sub(".", domain_part)
            # Re-validate through the strict regex so a reconstructed
            # candidate is held to the exact same shape as a plain match.
            revalidated = _EMAIL_RE.search(f"{local}@{domain}")
            candidate = revalidated.group(0) if revalidated else None
    if candidate:
        e = candidate.lower().strip(".")
        if len(e) <= 320 and "." in e.split("@")[-1]:
            return e
    return None


def extract_phone(bio: str | None) -> str | None:
    if not bio:
        return None
    normalized = _KEYCAP_DIGIT_RE.sub(r"\1", bio)
    m = _PHONE_RE.search(normalized)
    if m:
        d = re.sub(r"\D", "", m.group(0))
        if 8 <= len(d) <= 15:  # E.164's max length, was BR-only 8-13 (audit H5)
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
