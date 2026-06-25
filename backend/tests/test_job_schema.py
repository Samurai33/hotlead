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
