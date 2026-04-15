import pytest

from cs2_analytics.controllers import match_controller as match_module
from cs2_analytics.exceptions import MatchParseError, SessionScrapeError


class _FakeMatchQueue:
    def __init__(self) -> None:
        self.failed: list[tuple[str, str]] = []
        self.parsed: list[str] = []

    def fetch(self, limit: int = 25) -> list[tuple[str, str]]:
        return [("match-1", "https://www.hltv.org/matches/1/test")]

    def mark_as_failed(self, item_id: str, reason: str) -> None:
        self.failed.append((item_id, reason))

    def mark_as_parsed(self, item_id: str) -> None:
        self.parsed.append(item_id)


class _FakeFollowupQueue:
    def __init__(self) -> None:
        self.queued: list[tuple[str, str, str]] = []

    def queue(self, item_id: str, url: str, source: str = "unknown") -> None:
        self.queued.append((item_id, url, source))


class _PassiveScraper:
    def close(self) -> None:
        return None


class _AlwaysRetryableScraper(_PassiveScraper):
    def fetch_soup(self, url: str) -> None:
        raise SessionScrapeError(f"Failed to fetch match page: {url}")


class _SuccessfulScraper(_PassiveScraper):
    def fetch_soup(self, url: str) -> object:
        return object()


class _ParseFailureParser:
    def parse_match(self, soup: object, match_url: str) -> tuple[object, list, list]:
        raise MatchParseError("Missing team names on match page.")


class _SuccessfulParser:
    def parse_match(self, soup: object, match_url: str) -> tuple[object, list, list]:
        return object(), [], []


class _FailOnceThenSucceedParser:
    def __init__(self) -> None:
        self.calls = 0

    def parse_match(self, soup: object, match_url: str) -> tuple[object, list, list]:
        self.calls += 1
        if self.calls == 1:
            raise MatchParseError("Missing team names on match page.")
        return object(), [], []


def _build_match_controller(
    monkeypatch: pytest.MonkeyPatch,
    scraper_cls: type[_PassiveScraper],
    parser_cls: type[object],
) -> match_module.MatchController:
    monkeypatch.setattr(match_module, "MatchScraper", scraper_cls)
    monkeypatch.setattr(match_module, "MatchParser", parser_cls)
    monkeypatch.setattr(match_module, "MatchScrapeQueue", _FakeMatchQueue)
    monkeypatch.setattr(match_module, "MapScrapeQueue", _FakeFollowupQueue)
    monkeypatch.setattr(match_module, "DemoScrapeQueue", _FakeFollowupQueue)
    monkeypatch.setattr(match_module, "store_matches", lambda matches: None)
    monkeypatch.setattr(match_module.time, "sleep", lambda *_args, **_kwargs: None)
    return match_module.MatchController()


def test_match_controller_marks_non_retryable_parse_error_failed_immediately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_match_controller(
        monkeypatch,
        _SuccessfulScraper,
        _ParseFailureParser,
    )
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        match_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )

    controller.run(batch_size=1)

    assert controller.match_queue.failed == [
        ("match-1", "Missing team names on match page.")
    ]
    assert controller.match_queue.parsed == []
    assert len(exception_calls) == 1


def test_match_controller_marks_failed_once_after_exhausting_retryable_scrape_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_match_controller(
        monkeypatch,
        _AlwaysRetryableScraper,
        _SuccessfulParser,
    )
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        match_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(controller, "_reset_scraper", lambda scraper: scraper)

    controller.run(batch_size=1)

    assert len(controller.match_queue.failed) == 1
    failed_id, reason = controller.match_queue.failed[0]
    assert failed_id == "match-1"
    assert "Failed to fetch match page" in reason
    assert len(exception_calls) == 1


def test_match_controller_continues_after_item_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored_matches: list[list[object]] = []
    controller = _build_match_controller(
        monkeypatch,
        _SuccessfulScraper,
        _FailOnceThenSucceedParser,
    )
    monkeypatch.setattr(
        controller.match_queue,
        "fetch",
        lambda limit=25: [
            ("match-1", "https://www.hltv.org/matches/1/test"),
            ("match-2", "https://www.hltv.org/matches/2/test"),
        ],
    )
    monkeypatch.setattr(
        match_module,
        "store_matches",
        lambda matches: stored_matches.append(matches),
    )

    controller.run(batch_size=2)

    assert controller.match_queue.failed == [
        ("match-1", "Missing team names on match page.")
    ]
    assert controller.match_queue.parsed == ["match-2"]
    assert len(stored_matches) == 1
