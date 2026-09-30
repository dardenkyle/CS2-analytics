import pytest

from cs2_analytics.exceptions import SessionScrapeError
from cs2_analytics.scrapers import map_scraper as map_scraper_module
from cs2_analytics.scrapers import page_wait as page_wait_module
from cs2_analytics.scrapers.map_scraper import MapScraper
from tests.scrapers.page_fakes import FakeDriver, FakePollingWait

MAP_URL = "https://www.hltv.org/stats/matches/mapstatsid/1/test"


def _build_scraper(
    monkeypatch: pytest.MonkeyPatch,
    driver: FakeDriver,
) -> MapScraper:
    monkeypatch.setattr(map_scraper_module, "Driver", lambda **_kwargs: driver)
    monkeypatch.setattr(page_wait_module, "WebDriverWait", FakePollingWait)
    return MapScraper(content_wait_seconds=0.1)


def _capture_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[tuple[object, ...], dict[str, object]]]:
    warning_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        page_wait_module.logger,
        "warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )
    return warning_calls


def test_map_scraper_waits_for_required_match_info_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver(
        "<html><body><div class='match-info-box'>Ancient</div></body></html>",
    )
    scraper = _build_scraper(monkeypatch, driver)

    soup = scraper.fetch_soup(MAP_URL)

    assert soup.select_one("div.match-info-box") is not None
    assert driver.loaded_urls == [MAP_URL]
    assert driver.find_calls == [
        ("css selector", map_scraper_module.REQUIRED_MAP_SELECTOR)
    ]


def test_map_scraper_missing_match_info_box_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver(
        "<html><head><title>Just a moment...</title></head>"
        "<body>Checking your browser before accessing HLTV.</body></html>",
        renders_after_polls=None,
    )
    warning_calls = _capture_warnings(monkeypatch)
    scraper = _build_scraper(monkeypatch, driver)

    with pytest.raises(
        SessionScrapeError,
        match="Map stats page appears blocked or challenged after 0.1s",
    ):
        scraper.fetch_soup(MAP_URL)

    assert driver.find_calls[0] == (
        "css selector",
        map_scraper_module.REQUIRED_MAP_SELECTOR,
    )
    assert len(warning_calls) == 1
    rendered_warning = warning_calls[0][0][0] % warning_calls[0][0][1:]
    assert rendered_warning.startswith(
        "Map stats page missing required selector=div.match-info-box"
    )


def test_map_scraper_missing_match_info_box_without_challenge_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = FakeDriver(
        "<html><body>temporarily incomplete stats page</body></html>",
        renders_after_polls=None,
    )
    scraper = _build_scraper(monkeypatch, driver)

    with pytest.raises(
        SessionScrapeError,
        match="Map stats page missing required content after 0.1s",
    ):
        scraper.fetch_soup(MAP_URL)
