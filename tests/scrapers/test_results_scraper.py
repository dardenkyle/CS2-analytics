"""Tests for the fetch-only results scraper."""

import pytest

from cs2_analytics.scrapers import results_scraper as results_scraper_module
from cs2_analytics.scrapers.results_scraper import ResultsScraper


class _FakeDriver:
    def __init__(self, *args, **kwargs) -> None:
        self.quit_called = False

    def quit(self) -> None:
        self.quit_called = True


@pytest.fixture
def scraper(monkeypatch: pytest.MonkeyPatch) -> ResultsScraper:
    monkeypatch.setattr(results_scraper_module, "Driver", _FakeDriver)
    monkeypatch.setattr(
        results_scraper_module.time, "sleep", lambda *_args, **_kwargs: None
    )
    return ResultsScraper()


def _page(urls: list[str], stop: bool) -> tuple[list[str], bool]:
    return urls, stop


def test_iter_match_batches_yields_page_batches_with_ids(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = iter(
        [
            _page(
                [
                    "https://www.hltv.org/matches/111/a-vs-b",
                    "https://www.hltv.org/matches/222/c-vs-d",
                    "https://www.hltv.org/results/not-a-match",
                ],
                stop=False,
            ),
            _page(["https://www.hltv.org/matches/333/e-vs-f"], stop=True),
        ]
    )
    monkeypatch.setattr(scraper, "_extract_matches_from_page", lambda _url: next(pages))

    batches = list(scraper.iter_match_batches(max_matches=50))

    assert batches == [
        [
            (111, "https://www.hltv.org/matches/111/a-vs-b"),
            (222, "https://www.hltv.org/matches/222/c-vs-d"),
        ],
        [(333, "https://www.hltv.org/matches/333/e-vs-f")],
    ]


def test_iter_match_batches_stops_at_max_matches(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fake_extract(_url: str) -> tuple[list[str], bool]:
        nonlocal calls
        calls += 1
        return [f"https://www.hltv.org/matches/{calls}00/x-vs-y"], False

    monkeypatch.setattr(scraper, "_extract_matches_from_page", fake_extract)

    batches = list(scraper.iter_match_batches(max_matches=2))

    assert len(batches) == 2
    assert calls == 2


def test_iter_match_batches_stops_on_empty_page(
    scraper: ResultsScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scraper, "_extract_matches_from_page", lambda _url: ([], False))

    assert list(scraper.iter_match_batches(max_matches=10)) == []


def test_extract_match_id(scraper: ResultsScraper) -> None:
    assert (
        scraper._extract_match_id("https://www.hltv.org/matches/12345/a-vs-b") == 12345
    )
    assert scraper._extract_match_id("https://www.hltv.org/results") is None
