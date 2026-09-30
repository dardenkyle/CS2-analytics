"""Tests for the fetch-only match scraper."""

import pytest

from cs2_analytics.exceptions import (
    MatchParseError,
    MatchScrapeError,
    SessionScrapeError,
)
from cs2_analytics.parsers.match_parser import MatchParser
from cs2_analytics.scrapers import map_scraper as map_scraper_module
from cs2_analytics.scrapers import match_scraper as match_scraper_module
from cs2_analytics.scrapers import page_wait as page_wait_module
from cs2_analytics.scrapers.match_scraper import MatchScraper
from tests.scrapers.page_fakes import FakeDriver, FakePollingWait

MATCH_URL = "https://www.hltv.org/matches/2376231/test"
CHALLENGE_PAGE = (
    "<html><head><title>Just a moment...</title></head>"
    "<body>Enable JavaScript and cookies to continue. cloudflare</body></html>"
)
RENDERED_PAGE = (
    "<html><body><div class='match-page'>"
    "<div class='teamName'>Team One</div>"
    "<div class='teamName'>Team Two</div>"
    "</div></body></html>"
)
RENDERED_PAGE_EMPTY_TEAMS = (
    "<html><body><div class='match-page'>"
    "<div class='teamName'></div>"
    "<div class='teamName'></div>"
    "</div></body></html>"
)


class _FailingQuitDriver:
    def __init__(self, *args, **kwargs) -> None:
        self.quit_calls = 0

    def quit(self) -> None:
        self.quit_calls += 1
        raise RuntimeError("browser already gone")


def _build_scraper(
    monkeypatch: pytest.MonkeyPatch,
    driver: FakeDriver,
) -> MatchScraper:
    monkeypatch.setattr(match_scraper_module, "Driver", lambda **_kwargs: driver)
    monkeypatch.setattr(page_wait_module, "WebDriverWait", FakePollingWait)
    return MatchScraper(content_wait_seconds=0.1)


def _capture_log(
    monkeypatch: pytest.MonkeyPatch,
    level: str,
) -> list[tuple[object, ...]]:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        page_wait_module.logger,
        level,
        lambda *args, **kwargs: calls.append(args),
    )
    return calls


def test_close_failure_raises_typed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(match_scraper_module, "Driver", _FailingQuitDriver)
    scraper = MatchScraper()

    with pytest.raises(
        MatchScrapeError, match="Failed to close match scraper driver."
    ) as exc_info:
        scraper.close()

    assert scraper.driver.quit_calls == 1
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_challenge_page_raises_retryable_session_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver(CHALLENGE_PAGE, renders_after_polls=None)
    warning_calls = _capture_log(monkeypatch, "warning")
    scraper = _build_scraper(monkeypatch, driver)

    with pytest.raises(
        SessionScrapeError,
        match=(
            r"Match page appears blocked or challenged after 0\.1s "
            r"\(markers: cloudflare, enable_javascript, just_a_moment\)"
        ),
    ):
        scraper.fetch_soup(MATCH_URL)

    assert driver.find_calls[0] == (
        "css selector",
        match_scraper_module.REQUIRED_MATCH_SELECTOR,
    )
    assert len(warning_calls) == 1
    rendered_warning = warning_calls[0][0] % warning_calls[0][1:]
    assert rendered_warning.startswith(
        "Match page missing required selector=div.teamName"
    )
    assert "marker_flags=" in rendered_warning


def test_unrendered_page_without_markers_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver(
        "<html><body>still loading</body></html>", renders_after_polls=None
    )
    scraper = _build_scraper(monkeypatch, driver)

    with pytest.raises(
        SessionScrapeError,
        match="Match page missing required content after 0.1s",
    ):
        scraper.fetch_soup(MATCH_URL)


def test_slow_page_that_renders_within_wait_parses_normally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver(RENDERED_PAGE, renders_after_polls=2)
    info_calls = _capture_log(monkeypatch, "info")
    scraper = _build_scraper(monkeypatch, driver)

    soup = scraper.fetch_soup(MATCH_URL)
    team1, team2 = MatchParser()._extract_teams(soup)

    assert (team1, team2) == ("Team One", "Team Two")
    assert len(driver.find_calls) == 3
    assert driver.loaded_urls == [MATCH_URL]
    rendered_info = [args[0] % args[1:] for args in info_calls]
    assert any(
        line.startswith(f"Match page fetched url={MATCH_URL} elapsed_seconds=")
        for line in rendered_info
    )


def test_rendered_page_with_empty_team_names_still_raises_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver(RENDERED_PAGE_EMPTY_TEAMS)
    scraper = _build_scraper(monkeypatch, driver)

    soup = scraper.fetch_soup(MATCH_URL)

    with pytest.raises(MatchParseError, match="Missing team names on match page."):
        MatchParser().parse_match(soup, MATCH_URL)


def test_driver_failure_is_wrapped_as_session_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenDriver(FakeDriver):
        def get(self, url: str) -> None:
            raise RuntimeError("chrome crashed")

    scraper = _build_scraper(monkeypatch, _BrokenDriver(RENDERED_PAGE))

    with pytest.raises(SessionScrapeError, match="Failed to fetch match page") as exc:
        scraper.fetch_soup(MATCH_URL)

    assert isinstance(exc.value.__cause__, RuntimeError)


def test_both_scrapers_share_one_challenge_marker_definition() -> None:
    assert not hasattr(map_scraper_module, "CHALLENGE_MARKERS")
    assert not hasattr(match_scraper_module, "CHALLENGE_MARKERS")
    assert "just a moment" in page_wait_module.CHALLENGE_MARKERS
    assert (
        map_scraper_module.fetch_rendered_page
        is match_scraper_module.fetch_rendered_page
        is page_wait_module.fetch_rendered_page
    )
