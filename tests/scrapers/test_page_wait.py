"""Tests for the shared challenge-marker rule in `scrapers/page_wait.py`.

The match, map, and results scrapers all report a missing selector through
`challenge_marker_flags`, so its contract is pinned here once (#260).
"""

import pytest

from cs2_analytics.scrapers.page_wait import (
    INTERSTITIAL_MAX_LENGTH,
    challenge_marker_flags,
)


def _flagged(page_source: str) -> list[str]:
    return [
        marker
        for marker, is_present in challenge_marker_flags(page_source).items()
        if is_present
    ]


def _padded_to(page_source: str, length: int) -> str:
    """Pad the body with filler markup so the source is exactly `length` long."""
    filler = "x" * (length - len(page_source))
    return page_source.replace("</body>", f"{filler}</body>")


def _rendered_page(title: str, body: str, length: int) -> str:
    return _padded_to(
        f"<html><head><title>{title}</title></head><body>{body}</body></html>",
        length,
    )


HIDDEN_FORM_AND_COMMENT = (
    "<div class='match-page'><div hidden>Please complete the captcha</div>"
    "<div class='comment'>just a moment, stream lagging</div></div>"
)


def test_large_page_ignores_hidden_and_user_text_markers() -> None:
    page = _rendered_page("Match page", HIDDEN_FORM_AND_COMMENT, 300_000)

    assert _flagged(page) == []


def test_large_page_with_a_challenge_title_is_flagged() -> None:
    page = _rendered_page("Just a moment...", "<p>verify you are human</p>", 300_000)

    assert _flagged(page) == ["just_a_moment"]


@pytest.mark.parametrize(
    ("length", "expected"),
    [
        (INTERSTITIAL_MAX_LENGTH, ["captcha", "just_a_moment"]),
        (INTERSTITIAL_MAX_LENGTH + 1, []),
    ],
)
def test_body_markers_count_up_to_the_interstitial_length(
    length: int,
    expected: list[str],
) -> None:
    page = _rendered_page("Match page", HIDDEN_FORM_AND_COMMENT, length)

    assert len(page) == length
    assert _flagged(page) == expected


def test_non_visible_content_does_not_count_on_a_small_page() -> None:
    page = (
        "<html><head><title>Match page</title>"
        "<script>var captchaKey = 'abc';</script>"
        "<style>.cloudflare-badge { display: none; }</style></head><body>"
        "<noscript>Enable JavaScript to continue.</noscript>"
        "<template><p>Verify you are human</p></template>"
        "<div data-provider='access denied'>Team One 16 - 9 Team Two</div>"
        "</body></html>"
    )

    assert _flagged(page) == []


def test_page_without_a_title_uses_only_the_size_gated_body() -> None:
    small = "<html><body><p>Checking your browser</p></body></html>"
    large = _padded_to(small, INTERSTITIAL_MAX_LENGTH + 1)

    assert _flagged(small) == ["checking_your_browser"]
    assert _flagged(large) == []
