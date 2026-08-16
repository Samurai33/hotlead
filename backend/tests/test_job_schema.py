import pytest
from pydantic import ValidationError

from app.schemas.job import JobCreate


def test_commenters_requires_instagram_post_url():
    with pytest.raises(ValidationError, match="target_post_url must be an Instagram"):
        JobCreate(
            profile_username="cozinha4e20",
            mode="commenters",
            target_post_url="https://example.com/p/ABC123/",
        )


def test_commenters_accepts_and_strips_instagram_post_url():
    payload = JobCreate(
        profile_username="cozinha4e20",
        mode="commenters",
        target_post_url=" https://www.instagram.com/reel/ABC123/ ",
    )

    assert payload.target_post_url == "https://www.instagram.com/reel/ABC123/"


def test_non_commenters_may_omit_target_post_url():
    payload = JobCreate(profile_username="cozinha4e20", mode="followers")

    assert payload.target_post_url is None


def test_max_count_defaults_to_none():
    payload = JobCreate(profile_username="cozinha4e20")
    assert payload.max_count is None


def test_max_count_must_be_positive():
    with pytest.raises(ValidationError):
        JobCreate(profile_username="cozinha4e20", max_count=0)


def test_profile_username_over_max_length_rejected():
    """audit B7: profile_username backs a String(100) column -- oversized
    input must 422 in Pydantic, not fail at INSERT with StringDataRightTruncation."""
    with pytest.raises(ValidationError):
        JobCreate(profile_username="x" * 101)


def test_profile_username_at_max_length_accepted():
    payload = JobCreate(profile_username="x" * 100)
    assert len(payload.profile_username) == 100


def test_profile_username_rejects_non_instagram_charset():
    """audit AUDIT-3.md M1: profile_username flows unescaped into the
    export route's Content-Disposition filename -- reject anything outside
    Instagram's own charset instead of only relying on downstream escaping."""
    with pytest.raises(ValidationError):
        JobCreate(profile_username='cozinha"; evil')


def test_profile_username_accepts_dots_and_underscores():
    payload = JobCreate(profile_username="cozinha.4e20_oficial")
    assert payload.profile_username == "cozinha.4e20_oficial"


def test_target_post_url_over_max_length_rejected():
    """audit B7: target_post_url backs a String(500) column."""
    oversized = "https://www.instagram.com/p/" + ("A" * 480) + "/"
    assert len(oversized) > 500
    with pytest.raises(ValidationError):
        JobCreate(
            profile_username="cozinha4e20",
            mode="commenters",
            target_post_url=oversized,
        )
