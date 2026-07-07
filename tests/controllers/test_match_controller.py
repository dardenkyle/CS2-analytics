import pytest

from cs2_analytics.controllers import match_controller as match_module
from cs2_analytics.exceptions import MatchParseError, SessionScrapeError
from tests.support import FakeTransactionDb


class _FakeMatchState:
    def __init__(self) -> None:
        self.failed: list[tuple[int, str]] = []
        self.processed: list[int] = []
        self.processing: list[int] = []

    def fetch(self, limit: int = 25) -> list[tuple[int, str]]:
        assert limit > 0
        return [(1, "https://www.hltv.org/matches/1/test")]

    def mark_as_failed(self, item_id: int, reason: str) -> None:
        self.failed.append((item_id, reason))

    def mark_as_processed(self, item_id: int, cur=None) -> None:
        self.processed.append(item_id)

    def mark_as_processing(self, item_id: int) -> None:
        self.processing.append(item_id)


class _FakeFollowupState:
    def __init__(self) -> None:
        self.recorded: list[tuple[int | str, str, str, int | None]] = []

    def queue(
        self,
        item_id: int | str,
        url: str,
        source: str = "unknown",
        match_id: int | None = None,
        map_order: int | None = None,
        cur=None,
    ) -> None:
        self.recorded.append((item_id, url, source, match_id))


class _PassiveScraper:
    def close(self) -> None:
        return None


class _AlwaysRetryableScraper(_PassiveScraper):
    def fetch_soup(self, url: str) -> None:
        raise SessionScrapeError(f"Failed to fetch match page: {url}")


class _RetryTwiceThenSucceedScraper(_PassiveScraper):
    def __init__(self) -> None:
        self.calls = 0

    def fetch_soup(self, url: str) -> object:
        self.calls += 1
        if self.calls <= 2:
            raise SessionScrapeError(f"Failed to fetch match page: {url}")
        return object()


class _SuccessfulScraper(_PassiveScraper):
    def fetch_soup(self, url: str) -> object:
        assert url
        return object()


class _ParseFailureParser:
    def parse_match(self, _soup: object, _match_url: str) -> tuple[object, list, list]:
        raise MatchParseError("Missing team names on match page.")


class _SuccessfulParser:
    def parse_match(self, _soup: object, _match_url: str) -> tuple[object, list, list]:
        return object(), [], []


class _FailOnceThenSucceedParser:
    def __init__(self) -> None:
        self.calls = 0

    def parse_match(self, _soup: object, _match_url: str) -> tuple[object, list, list]:
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
    monkeypatch.setattr(match_module, "MatchIngestionState", _FakeMatchState)
    monkeypatch.setattr(match_module, "MapIngestionState", _FakeFollowupState)
    monkeypatch.setattr(match_module, "DemoIngestionState", _FakeFollowupState)
    monkeypatch.setattr(match_module, "store_matches", lambda _matches, cur=None: None)
    monkeypatch.setattr(match_module, "get_db", lambda: FakeTransactionDb())
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
    reset_calls: list[object] = []
    monkeypatch.setattr(
        match_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )

    controller.run(batch_size=1)

    assert controller.match_state.failed == [(1, "Missing team names on match page.")]
    assert controller.match_state.processed == []
    assert controller.match_state.processing == [1]
    assert len(exception_calls) == 1
    assert reset_calls == []


def test_match_controller_marks_failed_once_after_exhausting_retryable_scrape_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_match_controller(
        monkeypatch,
        _AlwaysRetryableScraper,
        _SuccessfulParser,
    )
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    error_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    reset_calls: list[object] = []
    monkeypatch.setattr(
        match_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        match_module.logger,
        "error",
        lambda *args, **kwargs: error_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        match_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )

    controller.run(batch_size=1)

    assert len(controller.match_state.failed) == 1
    failed_id, reason = controller.match_state.failed[0]
    assert failed_id == 1
    assert "Failed to fetch match page" in reason
    assert len(exception_calls) == 1
    assert len(reset_calls) == 2
    assert error_calls == [
        (
            (
                "Exhausted retries for match %s after %d attempts; marking failed and continuing.",
                1,
                3,
            ),
            {},
        )
    ]
    assert any(
        call_args[0]
        == "MatchController summary: selected=%d succeeded=%d failed=%d retries=%d"
        and call_args[1:] == (1, 0, 1, 2)
        for call_args, _ in info_calls
    )


def test_match_controller_continues_after_item_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored_matches: list[list[object]] = []
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    controller = _build_match_controller(
        monkeypatch,
        _SuccessfulScraper,
        _FailOnceThenSucceedParser,
    )
    monkeypatch.setattr(
        match_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )

    def _fetch_two_matches(limit: int = 25) -> list[tuple[int, str]]:
        assert limit == 2
        return [
            (1, "https://www.hltv.org/matches/1/test"),
            (2, "https://www.hltv.org/matches/2/test"),
        ]

    monkeypatch.setattr(
        controller.match_state,
        "fetch",
        _fetch_two_matches,
    )
    monkeypatch.setattr(
        controller.stage_service,
        "store_matches",
        lambda matches, cur=None: stored_matches.append(matches),
    )

    controller.run(batch_size=2)

    assert controller.match_state.failed == [(1, "Missing team names on match page.")]
    assert controller.match_state.processed == [2]
    assert controller.match_state.processing == [1, 2]
    assert len(stored_matches) == 1
    assert any(
        call_args[0]
        == "MatchController summary: selected=%d succeeded=%d failed=%d retries=%d"
        and call_args[1:] == (2, 1, 1, 0)
        for call_args, _ in info_calls
    )


def test_match_controller_applies_cooldown_after_consecutive_retryable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleep_calls: list[float] = []
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    stored_matches: list[list[object]] = []
    reset_calls: list[object] = []
    controller = _build_match_controller(
        monkeypatch,
        _RetryTwiceThenSucceedScraper,
        _SuccessfulParser,
    )
    monkeypatch.setattr(
        match_module.time,
        "sleep",
        lambda seconds, *_args, **_kwargs: sleep_calls.append(seconds),
    )
    monkeypatch.setattr(
        match_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )
    monkeypatch.setattr(
        controller.stage_service,
        "store_matches",
        lambda matches, cur=None: stored_matches.append(matches),
    )

    controller.run(batch_size=1)

    assert controller.match_state.failed == []
    assert controller.match_state.processed == [1]
    assert len(stored_matches) == 1
    assert len(reset_calls) == 2
    assert 8.0 in sleep_calls
    assert any(
        call_args[0] == "Applying cooldown after %d consecutive recoverable errors"
        and call_args[1:] == (2,)
        for call_args, _ in info_calls
    )
    assert any(
        call_args[0]
        == "MatchController summary: selected=%d succeeded=%d failed=%d retries=%d"
        and call_args[1:] == (1, 1, 0, 2)
        for call_args, _ in info_calls
    )
