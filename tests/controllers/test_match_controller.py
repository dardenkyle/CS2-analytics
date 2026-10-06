from unittest import mock

import pytest

from cs2_analytics.controllers import match_controller as match_module
from cs2_analytics.controllers.retry_utils import (
    CIRCUIT_BREAKER_THRESHOLD,
    BatchOutcome,
)
from cs2_analytics.exceptions import (
    DatabaseConnectionError,
    MatchParseError,
    SessionScrapeError,
)
from tests.support import ConnectionLossDb, FakeTransactionDb

MATCH_SUMMARY = (
    "MatchController summary: outcome=%s selected=%d succeeded=%d "
    "failed=%d retries=%d"
)


class _FakeMatchState:
    table_name = "match_ingestion_state"
    orphaned_processing = 0

    def __init__(self) -> None:
        self.failed: list[tuple[int, str]] = []
        self.processed: list[int] = []
        self.processing: list[int] = []
        self.requeued: list[tuple[list[int], str]] = []
        self.calls: list[str] = []

    def release_orphaned_processing(self) -> int:
        self.calls.append("release")
        return self.orphaned_processing

    def requeue(self, ids: list[int], expected_status: str) -> int:
        self.requeued.append((list(ids), expected_status))
        return len(ids)

    def fetch(self, limit: int = 25) -> list[tuple[int, str]]:
        assert limit > 0
        self.calls.append("fetch")
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
    db: FakeTransactionDb | None = None,
) -> match_module.MatchController:
    monkeypatch.setattr(match_module, "MatchScraper", scraper_cls)
    monkeypatch.setattr(match_module, "MatchParser", parser_cls)
    monkeypatch.setattr(match_module, "MatchIngestionState", _FakeMatchState)
    monkeypatch.setattr(match_module, "MapIngestionState", _FakeFollowupState)
    monkeypatch.setattr(match_module, "DemoIngestionState", _FakeFollowupState)
    monkeypatch.setattr(match_module, "store_matches", lambda _matches, cur=None: None)
    monkeypatch.setattr(match_module, "get_db", lambda: db or FakeTransactionDb())
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
        call_args[0] == MATCH_SUMMARY
        and call_args[1:] == ("completed", 1, 0, 1, 2)
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
        call_args[0] == MATCH_SUMMARY
        and call_args[1:] == ("completed", 2, 1, 1, 0)
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
        call_args[0] == MATCH_SUMMARY
        and call_args[1:] == ("completed", 1, 1, 0, 2)
        for call_args, _ in info_calls
    )


def test_match_controller_releases_orphaned_processing_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_match_controller(
        monkeypatch, _SuccessfulScraper, _SuccessfulParser
    )
    monkeypatch.setattr(_FakeMatchState, "orphaned_processing", 3)

    with mock.patch.object(match_module.logger, "warning") as warning_mock:
        controller.run(batch_size=5)

    assert controller.match_state.calls[:2] == ["release", "fetch"]
    release_warnings = [
        call for call in warning_mock.call_args_list
        if "orphaned" in str(call.args[0])
    ]
    assert len(release_warnings) == 1
    assert release_warnings[0].args[1] == 3
    assert release_warnings[0].args[2] == "match_ingestion_state"


def test_match_controller_stays_quiet_when_nothing_is_orphaned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_match_controller(
        monkeypatch, _SuccessfulScraper, _SuccessfulParser
    )
    monkeypatch.setattr(_FakeMatchState, "orphaned_processing", 0)

    with mock.patch.object(match_module.logger, "warning") as warning_mock:
        controller.run(batch_size=5)

    assert controller.match_state.calls[0] == "release"
    assert not any("orphaned" in str(c.args[0]) for c in warning_mock.call_args_list)


def _capture_match_log(
    monkeypatch: pytest.MonkeyPatch, level: str
) -> list[tuple[object, ...]]:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        match_module.logger, level, lambda *args, **_kwargs: calls.append(args)
    )
    return calls


def _track_match_resets(
    monkeypatch: pytest.MonkeyPatch, controller: match_module.MatchController
) -> list[object]:
    reset_calls: list[object] = []
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )
    return reset_calls


MATCH_STORAGE_RETRY = "Retryable storage error for match %s (attempt %d/%d): %s"


def test_match_controller_retries_lost_database_connection_then_stores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = ConnectionLossDb(losses=1)
    controller = _build_match_controller(
        monkeypatch, _SuccessfulScraper, _SuccessfulParser, db=db
    )
    sleeps: list[float] = []
    monkeypatch.setattr(match_module.time, "sleep", sleeps.append)
    warning_calls = _capture_match_log(monkeypatch, "warning")
    info_calls = _capture_match_log(monkeypatch, "info")
    reset_calls = _track_match_resets(monkeypatch, controller)

    controller.run(batch_size=1)

    assert controller.match_state.failed == []
    assert controller.match_state.processed == [1]
    assert db.attempts == 2
    assert reset_calls == []
    assert len(warning_calls) == 1
    assert warning_calls[0][:4] == (MATCH_STORAGE_RETRY, 1, 1, 3)
    assert isinstance(warning_calls[0][4], DatabaseConnectionError)
    assert match_module.RETRY_BACKOFF_SECONDS in sleeps
    assert (MATCH_SUMMARY, "completed", 1, 1, 0, 1) in info_calls


def test_match_controller_marks_failed_after_connection_stays_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = ConnectionLossDb(losses=match_module.MAX_ATTEMPTS)
    controller = _build_match_controller(
        monkeypatch, _SuccessfulScraper, _SuccessfulParser, db=db
    )
    error_calls = _capture_match_log(monkeypatch, "error")
    exception_calls = _capture_match_log(monkeypatch, "exception")
    info_calls = _capture_match_log(monkeypatch, "info")
    reset_calls = _track_match_resets(monkeypatch, controller)

    controller.run(batch_size=1)

    assert controller.match_state.failed == [
        (1, "Database connection was lost during a transaction.")
    ]
    assert controller.match_state.processed == []
    assert db.attempts == match_module.MAX_ATTEMPTS
    assert reset_calls == []
    assert error_calls == [
        (
            "Exhausted retries for match %s after %d attempts; marking failed and continuing.",
            1,
            3,
        )
    ]
    assert len(exception_calls) == 1
    assert exception_calls[0][1:4] == (1, 3, 3)
    assert (MATCH_SUMMARY, "completed", 1, 0, 1, 2) in info_calls


def test_match_controller_fails_non_retryable_storage_error_on_first_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeTransactionDb(fail_on_exit=RuntimeError("violates check constraint"))
    controller = _build_match_controller(
        monkeypatch, _SuccessfulScraper, _SuccessfulParser, db=db
    )
    warning_calls = _capture_match_log(monkeypatch, "warning")
    error_calls = _capture_match_log(monkeypatch, "error")
    exception_calls = _capture_match_log(monkeypatch, "exception")
    info_calls = _capture_match_log(monkeypatch, "info")

    controller.run(batch_size=1)

    assert controller.match_state.failed == [(1, "Failed during database transaction.")]
    assert len(db.cursors) == 1
    assert warning_calls == []
    assert error_calls == []
    assert len(exception_calls) == 1
    assert exception_calls[0][1:4] == (1, 1, 3)
    assert (MATCH_SUMMARY, "completed", 1, 0, 1, 0) in info_calls


class _ScriptedScraper(_PassiveScraper):
    """Raises the retryable session error whenever `fails(url, nth_fetch)` says so."""

    def __init__(self) -> None:
        self.fetched: list[str] = []
        self.fails = lambda _url, _nth_fetch: False

    def fetch_soup(self, url: str) -> object:
        self.fetched.append(url)
        if self.fails(url, self.fetched.count(url)):
            raise SessionScrapeError(f"Failed to fetch match page: {url}")
        return object()


def _match_url(match_id: int) -> str:
    return f"https://example.test/matches/{match_id}"


def _build_scripted_match_controller(
    monkeypatch: pytest.MonkeyPatch, match_ids: list[int], fails
) -> match_module.MatchController:
    """Builds a controller over `match_ids` whose fetches fail as scripted."""
    controller = _build_match_controller(
        monkeypatch, _ScriptedScraper, _SuccessfulParser
    )
    controller.scraper.fails = fails
    monkeypatch.setattr(controller, "_reset_scraper", lambda scraper: scraper)
    monkeypatch.setattr(
        controller.match_state,
        "fetch",
        lambda **_kwargs: [
            (match_id, _match_url(match_id)) for match_id in match_ids
        ],
    )
    return controller


def test_match_controller_halts_batch_when_every_fetch_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_scripted_match_controller(
        monkeypatch, [1, 2, 3, 4], lambda _url, _nth_fetch: True
    )
    error_calls = _capture_match_log(monkeypatch, "error")
    warning_calls = _capture_match_log(monkeypatch, "warning")
    info_calls = _capture_match_log(monkeypatch, "info")

    outcome = controller.run(batch_size=4)

    assert outcome is BatchOutcome.HALTED
    # The breaker stops fetching at the threshold: three attempts at match
    # 1, two at match 2, and nothing for matches 3 and 4.
    assert controller.scraper.fetched == [_match_url(1)] * 3 + [_match_url(2)] * 2
    assert controller.match_state.processing == [1, 2]
    assert controller.match_state.processed == []
    assert [item_id for item_id, _reason in controller.match_state.failed] == [1]
    assert controller.match_state.requeued == [
        ([2], "processing"),
        ([1], "failed"),
    ]
    halt_calls = [call for call in error_calls if "circuit breaker" in call[0]]
    assert len(halt_calls) == 1
    assert halt_calls[0][1:4] == (
        "MatchController",
        CIRCUIT_BREAKER_THRESHOLD,
        CIRCUIT_BREAKER_THRESHOLD,
    )
    release_calls = [call for call in warning_calls if "halt returned" in call[0]]
    assert [call[1:] for call in release_calls] == [("MatchController", 1, 1, 4, 4)]
    assert (MATCH_SUMMARY, "halted", 4, 0, 0, 3) in info_calls
    assert ("MatchController %s.", "halted") in info_calls


def test_match_controller_does_not_halt_on_isolated_retryable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    match_ids = list(range(1, CIRCUIT_BREAKER_THRESHOLD + 2))
    controller = _build_scripted_match_controller(
        monkeypatch, match_ids, lambda _url, nth_fetch: nth_fetch == 1
    )

    outcome = controller.run(batch_size=len(match_ids))

    assert outcome is BatchOutcome.COMPLETED
    assert controller.match_state.processed == match_ids
    assert controller.match_state.failed == []
    assert controller.match_state.requeued == []


def test_match_controller_single_unfetchable_match_does_not_halt_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_scripted_match_controller(
        monkeypatch, [1, 2, 3], lambda url, _nth_fetch: url == _match_url(1)
    )

    outcome = controller.run(batch_size=3)

    assert outcome is BatchOutcome.COMPLETED
    assert [item_id for item_id, _reason in controller.match_state.failed] == [1]
    assert controller.match_state.processed == [2, 3]
    assert controller.match_state.requeued == []
