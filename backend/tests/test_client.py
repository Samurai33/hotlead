"""IGClient tests — instagrapi call-signature regression guard (audit M1
prerequisite) and cursor resume/callback wiring.

Uses create_autospec(instagrapi.Client) so a call with a keyword argument
instagrapi doesn't actually accept (e.g. the old `next_cursor=`, versus the
real `max_id=`) raises TypeError immediately — the same way it would against
a live account. Without autospec, a plain MagicMock silently accepts any
kwarg and this bug (present since the code was first written, not just the
2.1.2->2.18.1 dependency bump) would stay invisible to tests forever.
"""

from unittest.mock import create_autospec, patch

import pytest
from instagrapi import Client as RealClient

from app.scraper.client import IGClient


def _make_client() -> IGClient:
    with patch("app.scraper.client.Client") as mock_cls:
        mock_cls.return_value = create_autospec(RealClient, instance=True)
        cl = IGClient(username="tester", session_json='{"device_id": "test"}')
    cl._cl.user_id_from_username.return_value = "12345"
    return cl


def test_iter_followers_calls_real_instagrapi_signature():
    cl = _make_client()
    cl._cl.user_followers_v1_chunk.return_value = ([], "")

    list(cl.iter_followers("someprofile"))

    cl._cl.user_followers_v1_chunk.assert_called_once()
    _, kwargs = cl._cl.user_followers_v1_chunk.call_args
    assert kwargs.get("max_id") == ""
    assert "next_cursor" not in kwargs


def test_iter_following_calls_real_instagrapi_signature():
    cl = _make_client()
    cl._cl.user_following_v1_chunk.return_value = ([], "")

    list(cl.iter_following("someprofile"))

    cl._cl.user_following_v1_chunk.assert_called_once()
    _, kwargs = cl._cl.user_following_v1_chunk.call_args
    assert kwargs.get("max_id") == ""
    assert "next_cursor" not in kwargs


def test_iter_followers_resumes_from_start_cursor():
    """audit M1: a resumed/retried job must not restart pagination at page 1."""
    cl = _make_client()
    cl._cl.user_followers_v1_chunk.return_value = ([], "")

    list(cl.iter_followers("someprofile", start_cursor="saved_max_id_123"))

    _, kwargs = cl._cl.user_followers_v1_chunk.call_args
    assert kwargs.get("max_id") == "saved_max_id_123"


def test_iter_followers_on_cursor_called_per_page():
    cl = _make_client()
    cl._cl.user_followers_v1_chunk.side_effect = [
        ([], "page_2_cursor"),
        ([], ""),
    ]
    seen_cursors = []

    list(cl.iter_followers("someprofile", on_cursor=seen_cursors.append))

    assert seen_cursors == ["page_2_cursor", ""]


@pytest.mark.parametrize("bad_kwargs", [{"next_cursor": "x"}])
def test_real_instagrapi_signature_rejects_next_cursor(bad_kwargs):
    """Documents *why* the regression guard above matters: proves the mocked
    signature really does reject the old kwarg name, so a future instagrapi
    upgrade that silently re-adds `next_cursor` wouldn't make this suite
    falsely confident."""
    autospec = create_autospec(RealClient, instance=True)
    with pytest.raises(TypeError):
        autospec.user_followers_v1_chunk("uid", max_amount=50, **bad_kwargs)
