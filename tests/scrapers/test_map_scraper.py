import pytest
from selenium.common.exceptions import TimeoutException

from cs2_analytics.exceptions import SessionScrapeError
from cs2_analytics.scrapers import map_scraper as map_scraper_module
from cs2_analytics.scrapers.map_scraper import MapScraper


class _FakeDriver:
    def __init__(self, page_source: str, *, has_required_content: bool) -> None:
        self.page_source = page_source
        self.has_required_content = has_required_content
        self.current_url = "about:blank"
        self.title = "fake page"
        self.loaded_urls: list[str] = []
        self.find_calls: list[tuple[str, str]] = []
        self.quit_called = False

    def get(self, url: str) -> None:
        self.loaded_urls.append(url)
        self.current_url = url

    def find_element(self, by: str, selector: str) -> object:
        self.find_calls.append((by, selector))
        if self.has_required_content:
            return object()
        raise TimeoutException("missing required content")

    def quit(self) -> None:
        self.quit_called = True


class _FakeWait:
    def __init__(self, driver: _FakeDriver, _timeout: float) -> None:
        self.driver = driver

    def until(self, condition) -> object:
        try:
            return condition(self.driver)
        except TimeoutException:
            raise
        except Exception as exc:
            raise TimeoutException("condition timed out") from exc


def _build_scraper(
    monkeypatch: pytest.MonkeyPatch,
    driver: _FakeDriver,
) -> MapScraper:
    monkeypatch.setattr(map_scraper_module, "Driver", lambda **_kwargs: driver)
    monkeypatch.setattr(map_scraper_module, "WebDriverWait", _FakeWait)
    return MapScraper(content_wait_seconds=0.1)


def test_map_scraper_waits_for_required_match_info_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _FakeDriver(
        "<html><body><div class='match-info-box'>Ancient</div></body></html>",
        has_required_content=True,
    )
    scraper = _build_scraper(monkeypatch, driver)

    soup = scraper.fetch_soup("https://www.hltv.org/stats/matches/mapstatsid/1/test")

    assert soup.select_one("div.match-info-box") is not None
    assert driver.loaded_urls == [
        "https://www.hltv.org/stats/matches/mapstatsid/1/test"
    ]
    assert driver.find_calls == [
        ("css selector", map_scraper_module.REQUIRED_MAP_SELECTOR)
    ]


def test_map_scraper_missing_match_info_box_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _FakeDriver(
        "<html><head><title>Just a moment...</title></head>"
        "<body>Checking your browser before accessing HLTV.</body></html>",
        has_required_content=False,
    )
    warning_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        map_scraper_module.logger,
        "warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )
    scraper = _build_scraper(monkeypatch, driver)

    with pytest.raises(
        SessionScrapeError,
        match="Map stats page appears blocked or challenged after 0.1s",
    ):
        scraper.fetch_soup("https://www.hltv.org/stats/matches/mapstatsid/1/test")

    assert driver.find_calls == [
        ("css selector", map_scraper_module.REQUIRED_MAP_SELECTOR)
    ]
    assert len(warning_calls) == 1
    assert warning_calls[0][0][0].startswith(
        "Map stats page missing required selector=%s"
    )


def test_map_scraper_missing_match_info_box_without_challenge_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _FakeDriver(
        "<html><body>temporarily incomplete stats page</body></html>",
        has_required_content=False,
    )
    scraper = _build_scraper(monkeypatch, driver)

    with pytest.raises(
        SessionScrapeError,
        match="Map stats page missing required content after 0.1s",
    ):
        scraper.fetch_soup("https://www.hltv.org/stats/matches/mapstatsid/1/test")
