"""IGClient tests — instagrapi call-signature regression guard (audit M1
prerequisite) and cursor resume/callback wiring.

Uses create_autospec(instagrapi.Client) so a call with a keyword argument
instagrapi doesn't actually accept (e.g. the old `next_cursor=`, versus the
real `max_id=`) raises TypeError immediately — the same way it would against
a live account. Without autospec, a plain MagicMock silently accepts any
kwarg and this bug (present since the code was first written, not just the
2.1.2->2.18.1 dependency bump) would stay invisible to tests forever.
"""

from unittest.mock import MagicMock, create_autospec, patch

import pytest
from instagrapi import Client as RealClient
from instagrapi.exceptions import FeedbackRequired

from app.scraper.client import AccountFlagged, IGClient


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


def _commenter(pk: int, username: str):
    user = MagicMock(pk=pk, username=username, full_name=None, is_private=False, is_verified=False)
    return MagicMock(user=user)


def test_iter_commenters_paginates_beyond_single_chunk():
    """audit L8: commenters used to cap silently at 500 (one media_comments
    call, no pagination). Now walks pages via media_comments_chunk like the
    other two iterators."""
    cl = _make_client()
    cl._cl.media_pk_from_url.return_value = "media123"
    cl._cl.media_comments_chunk.side_effect = [
        ([_commenter(1, "u1")], "cursor_2"),
        ([_commenter(2, "u2")], ""),
    ]

    result = list(cl.iter_commenters("https://www.instagram.com/p/ABC/"))

    assert [r["username"] for r in result] == ["u1", "u2"]
    assert cl._cl.media_comments_chunk.call_count == 2
    _, kwargs = cl._cl.media_comments_chunk.call_args_list[0]
    assert kwargs.get("min_id") is None


def test_iter_commenters_dedupes_by_pk():
    cl = _make_client()
    cl._cl.media_pk_from_url.return_value = "media123"
    dup = _commenter(1, "dup")
    cl._cl.media_comments_chunk.return_value = ([dup, dup], "")

    result = list(cl.iter_commenters("https://www.instagram.com/p/ABC/"))
    assert len(result) == 1


def test_iter_commenters_resumes_from_start_cursor():
    cl = _make_client()
    cl._cl.media_pk_from_url.return_value = "media123"
    cl._cl.media_comments_chunk.return_value = ([], "")

    list(cl.iter_commenters("https://www.instagram.com/p/ABC/", start_cursor="saved_min_id"))

    _, kwargs = cl._cl.media_comments_chunk.call_args
    assert kwargs.get("min_id") == "saved_min_id"


def test_iter_commenters_respects_max_count_across_pages():
    cl = _make_client()
    cl._cl.media_pk_from_url.return_value = "media123"
    cl._cl.media_comments_chunk.side_effect = [
        ([_commenter(1, "u1"), _commenter(2, "u2")], "cursor_2"),
        ([_commenter(3, "u3")], ""),
    ]

    result = list(cl.iter_commenters("https://www.instagram.com/p/ABC/", max_count=2))

    assert [r["username"] for r in result] == ["u1", "u2"]
    assert cl._cl.media_comments_chunk.call_count == 1


def test_get_user_id_maps_feedback_required_to_account_flagged():
    """audit H2: FeedbackRequired (IG has already flagged the account) is a
    sibling exception to ChallengeRequired in instagrapi, not a variant --
    it was silently falling through to the generic except Exception."""
    cl = _make_client()
    cl._cl.user_id_from_username.side_effect = FeedbackRequired("flagged")

    with pytest.raises(AccountFlagged):
        cl.get_user_id("someprofile")


def test_iter_followers_maps_feedback_required_to_account_flagged():
    cl = _make_client()
    cl._cl.user_followers_v1_chunk.side_effect = FeedbackRequired("flagged")

    with pytest.raises(AccountFlagged):
        list(cl.iter_followers("someprofile"))


def test_iter_following_maps_feedback_required_to_account_flagged():
    cl = _make_client()
    cl._cl.user_following_v1_chunk.side_effect = FeedbackRequired("flagged")

    with pytest.raises(AccountFlagged):
        list(cl.iter_following("someprofile"))


def test_iter_commenters_maps_feedback_required_to_account_flagged():
    cl = _make_client()
    cl._cl.media_pk_from_url.return_value = "media123"
    cl._cl.media_comments_chunk.side_effect = FeedbackRequired("flagged")

    with pytest.raises(AccountFlagged):
        list(cl.iter_commenters("https://www.instagram.com/p/ABC/"))


@pytest.mark.parametrize("bad_kwargs", [{"next_cursor": "x"}])
def test_real_instagrapi_signature_rejects_next_cursor(bad_kwargs):
    """Documents *why* the regression guard above matters: proves the mocked
    signature really does reject the old kwarg name, so a future instagrapi
    upgrade that silently re-adds `next_cursor` wouldn't make this suite
    falsely confident."""
    autospec = create_autospec(RealClient, instance=True)
    with pytest.raises(TypeError):
        autospec.user_followers_v1_chunk("uid", max_amount=50, **bad_kwargs)
