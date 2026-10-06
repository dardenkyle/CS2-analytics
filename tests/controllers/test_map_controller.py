from unittest import mock

import pytest

from cs2_analytics.controllers import map_controller as map_module
from cs2_analytics.exceptions import (
    DatabaseConnectionError,
    MapParseError,
    SessionScrapeError,
)
from cs2_analytics.stage_services import StageItemResult
from tests.support import ConnectionLossDb, FakeTransactionDb


class _FakeMapState:
    table_name = "map_ingestion_state"
    orphaned_processing = 0

    def __init__(self) -> None:
        self.failed: list[tuple[int, str]] = []
        self.processed: list[int] = []
        self.processing: list[int] = []
        self.calls: list[str] = []

    def release_orphaned_processing(self) -> int:
        self.calls.append("release")
        return self.orphaned_processing

    def fetch_with_match_context(
        self, _limit: int = 25
    ) -> list[tuple[int, str, int | None, int | None]]:
        self.calls.append("fetch")
        return [
            (1, "https://www.hltv.org/stats/matches/mapstatsid/1/test", 101, 1),
            (2, "https://www.hltv.org/stats/matches/mapstatsid/2/test", 102, 2),
        ]

    def mark_as_failed(self, item_id: int, reason: str) -> None:
        self.failed.append((item_id, reason))

    def mark_as_processed(self, item_id: int, cur=None) -> None:
        self.processed.append(item_id)

    def mark_as_processing(self, item_id: int) -> None:
        self.processing.append(item_id)


class _SuccessfulScraper:
    def fetch_soup(self, _url: str) -> object:
        return object()

    def close(self) -> None:
        return None


class _AlwaysRetryableScraper(_SuccessfulScraper):
    def fetch_soup(self, url: str) -> object:
        raise SessionScrapeError(f"Failed to fetch map stats page: {url}")


class _RetryThenSucceedScraper(_SuccessfulScraper):
    def __init__(self) -> None:
        self.calls = 0

    def fetch_soup(self, url: str) -> object:
        self.calls += 1
        if self.calls == 1:
            raise SessionScrapeError(f"Failed to fetch map stats page: {url}")
        return object()


class _TrackingStageService:
    def __init__(self) -> None:
        self.scrapers: list[object] = []
        self.match_ids: list[int | None] = []
        self.map_orders: list[int | None] = []

    def process_item(
        self,
        _map_id: int,
        map_url: str,
        *,
        scraper: object,
        match_id: int | None = None,
        map_order: int | None = None,
    ) -> StageItemResult:
        self.scrapers.append(scraper)
        self.match_ids.append(match_id)
        self.map_orders.append(map_order)
        if len(self.scrapers) == 1:
            raise SessionScrapeError(f"Failed to fetch map stats page: {map_url}")
        return StageItemResult.processed()


class _FailOnceThenSucceedParser:
    def __init__(self) -> None:
        self.calls = 0

    def parse_map_details(
        self,
        _soup: object,
        _map_url: str,
        _map_id: int,
        *,
        match_id: int | None,
        map_order: int | None,
    ) -> object:
        _ = (match_id, map_order)
        self.calls += 1
        if self.calls == 1:
            raise MapParseError("No player kills logged.")
        return type("ParsedMap", (), {"map": object(), "players": [object()]})()


class _SuccessfulParser:
    def parse_map_details(
        self,
        _soup: object,
        _map_url: str,
        _map_id: int,
        *,
        match_id: int | None,
        map_order: int | None,
    ) -> object:
        _ = (match_id, map_order)
        return type("ParsedMap", (), {"map": object(), "players": [object()]})()


def _build_map_controller(
    monkeypatch: pytest.MonkeyPatch,
    scraper_cls: type[object],
    parser_cls: type[object],
    db: FakeTransactionDb | None = None,
) -> map_module.MapController:
    monkeypatch.setattr(map_module, "MapScraper", scraper_cls)
    monkeypatch.setattr(map_module, "MapParser", parser_cls)
    monkeypatch.setattr(map_module, "MapIngestionState", _FakeMapState)
    monkeypatch.setattr(map_module, "get_db", lambda: db or FakeTransactionDb())
    monkeypatch.setattr(
        map_module,
        "store_maps",
        lambda _maps, cur=None: None,
    )
    monkeypatch.setattr(
        map_module,
        "store_players",
        lambda _players, cur=None: None,
    )
    monkeypatch.setattr(map_module.time, "sleep", lambda *_args, **_kwargs: None)
    return map_module.MapController()


def test_map_controller_continues_after_item_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored_players: list[list[object]] = []
    stored_maps: list[list[object]] = []
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(map_module, "MapScraper", _SuccessfulScraper)
    monkeypatch.setattr(map_module, "MapParser", _FailOnceThenSucceedParser)
    monkeypatch.setattr(map_module, "MapIngestionState", _FakeMapState)
    monkeypatch.setattr(map_module, "get_db", lambda: FakeTransactionDb())
    monkeypatch.setattr(
        map_module,
        "store_maps",
        lambda maps, cur=None: stored_maps.append(maps),
    )
    monkeypatch.setattr(
        map_module,
        "store_players",
        lambda players, cur=None: stored_players.append(players),
    )
    monkeypatch.setattr(map_module.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        map_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )

    controller = map_module.MapController()
    controller.run(batch_size=2)

    assert controller.state.failed == [(1, "No player kills logged.")]
    assert controller.state.processed == [2]
    assert controller.state.processing == [1, 2]
    assert len(stored_maps) == 1
    assert len(stored_players) == 1
    assert any(
        call_args[0]
        == "MapController summary: selected=%d succeeded=%d failed=%d retries=%d"
        and call_args[1:] == (2, 1, 1, 0)
        for call_args, _ in info_calls
    )


def test_map_controller_retries_retryable_error_before_succeeding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    reset_calls: list[object] = []
    controller = _build_map_controller(
        monkeypatch,
        _RetryThenSucceedScraper,
        _SuccessfulParser,
    )
    stored_players: list[list[object]] = []
    stored_maps: list[list[object]] = []
    monkeypatch.setattr(
        controller.stage_service,
        "store_maps",
        lambda maps, cur=None: stored_maps.append(maps),
    )
    monkeypatch.setattr(
        controller.stage_service,
        "store_players",
        lambda players, cur=None: stored_players.append(players),
    )
    monkeypatch.setattr(
        map_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )
    monkeypatch.setattr(
        controller.state,
        "fetch_with_match_context",
        lambda _limit=25: [
            (1, "https://www.hltv.org/stats/matches/mapstatsid/1/test", 123, 1)
        ],
    )

    controller.run(batch_size=1)

    assert controller.state.failed == []
    assert controller.state.processed == [1]
    assert len(stored_maps) == 1
    assert len(stored_players) == 1
    assert len(reset_calls) == 1
    assert any(
        call_args[0]
        == "MapController summary: selected=%d succeeded=%d failed=%d retries=%d"
        and call_args[1:] == (1, 1, 0, 1)
        for call_args, _ in info_calls
    )


def test_map_controller_passes_reset_scraper_to_stage_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_map_controller(
        monkeypatch,
        _SuccessfulScraper,
        _SuccessfulParser,
    )
    first_scraper = controller.scraper
    reset_scraper = _SuccessfulScraper()
    stage_service = _TrackingStageService()
    monkeypatch.setattr(controller, "stage_service", stage_service)
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda _scraper: reset_scraper,
    )
    monkeypatch.setattr(
        controller.state,
        "fetch_with_match_context",
        lambda _limit=25: [
            (1, "https://www.hltv.org/stats/matches/mapstatsid/1/test", 123, 1)
        ],
    )

    controller.run(batch_size=1)

    assert stage_service.scrapers == [first_scraper, reset_scraper]
    assert stage_service.match_ids == [123, 123]
    assert stage_service.map_orders == [1, 1]
    assert controller.state.failed == []
    assert controller.state.processed == []


def test_map_controller_marks_failed_once_after_exhausting_retryable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    reset_calls: list[object] = []
    controller = _build_map_controller(
        monkeypatch,
        _AlwaysRetryableScraper,
        _SuccessfulParser,
    )
    monkeypatch.setattr(
        map_module.logger,
        "error",
        lambda *args, **kwargs: error_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        map_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        map_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )
    monkeypatch.setattr(
        controller.state,
        "fetch_with_match_context",
        lambda _limit=25: [
            (1, "https://www.hltv.org/stats/matches/mapstatsid/1/test", 123, 1)
        ],
    )

    controller.run(batch_size=1)

    assert controller.state.failed == [
        (
            1,
            "Failed to fetch map stats page: https://www.hltv.org/stats/matches/mapstatsid/1/test",
        )
    ]
    assert controller.state.processed == []
    assert len(reset_calls) == 2
    assert error_calls == [
        (
            (
                "Exhausted retries for map %s after %d attempts; marking failed and continuing.",
                1,
                3,
            ),
            {},
        )
    ]
    assert len(exception_calls) == 1
    assert any(
        call_args[0]
        == "MapController summary: selected=%d succeeded=%d failed=%d retries=%d"
        and call_args[1:] == (1, 0, 1, 2)
        for call_args, _ in info_calls
    )


def test_map_controller_releases_orphaned_processing_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_map_controller(
        monkeypatch, _SuccessfulScraper, _SuccessfulParser
    )
    monkeypatch.setattr(_FakeMapState, "orphaned_processing", 4)

    with mock.patch.object(map_module.logger, "warning") as warning_mock:
        controller.run(batch_size=5)

    assert controller.state.calls[:2] == ["release", "fetch"]
    release_warnings = [
        call for call in warning_mock.call_args_list
        if "orphaned" in str(call.args[0])
    ]
    assert len(release_warnings) == 1
    assert release_warnings[0].args[1] == 4
    assert release_warnings[0].args[2] == "map_ingestion_state"


def _capture_map_log(
    monkeypatch: pytest.MonkeyPatch, level: str
) -> list[tuple[object, ...]]:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        map_module.logger, level, lambda *args, **_kwargs: calls.append(args)
    )
    return calls


def _build_single_map_controller(
    monkeypatch: pytest.MonkeyPatch, db: FakeTransactionDb
) -> tuple[map_module.MapController, list[object]]:
    """Builds a controller with one pending map and tracked scraper resets."""
    controller = _build_map_controller(
        monkeypatch, _SuccessfulScraper, _SuccessfulParser, db=db
    )
    reset_calls: list[object] = []
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )
    monkeypatch.setattr(
        controller.state,
        "fetch_with_match_context",
        lambda _limit=25: [
            (1, "https://www.hltv.org/stats/matches/mapstatsid/1/test", 123, 1)
        ],
    )
    return controller, reset_calls


MAP_SUMMARY = "MapController summary: selected=%d succeeded=%d failed=%d retries=%d"
MAP_STORAGE_RETRY = "Retryable storage error for map %s (attempt %d/%d): %s"


def test_map_controller_retries_lost_database_connection_then_stores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = ConnectionLossDb(losses=1)
    controller, reset_calls = _build_single_map_controller(monkeypatch, db)
    sleeps: list[float] = []
    monkeypatch.setattr(map_module.time, "sleep", sleeps.append)
    warning_calls = _capture_map_log(monkeypatch, "warning")
    info_calls = _capture_map_log(monkeypatch, "info")

    controller.run(batch_size=1)

    assert controller.state.failed == []
    assert controller.state.processed == [1]
    assert db.attempts == 2
    assert reset_calls == []
    assert len(warning_calls) == 1
    assert warning_calls[0][:4] == (MAP_STORAGE_RETRY, 1, 1, 3)
    assert isinstance(warning_calls[0][4], DatabaseConnectionError)
    assert map_module.RETRY_BACKOFF_SECONDS in sleeps
    assert (MAP_SUMMARY, 1, 1, 0, 1) in info_calls


def test_map_controller_marks_failed_after_connection_stays_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = ConnectionLossDb(losses=map_module.MAX_ATTEMPTS)
    controller, reset_calls = _build_single_map_controller(monkeypatch, db)
    error_calls = _capture_map_log(monkeypatch, "error")
    exception_calls = _capture_map_log(monkeypatch, "exception")
    info_calls = _capture_map_log(monkeypatch, "info")

    controller.run(batch_size=1)

    assert controller.state.failed == [
        (1, "Database connection was lost during a transaction.")
    ]
    assert controller.state.processed == []
    assert db.attempts == map_module.MAX_ATTEMPTS
    assert reset_calls == []
    assert error_calls == [
        (
            "Exhausted retries for map %s after %d attempts; marking failed and continuing.",
            1,
            3,
        )
    ]
    assert len(exception_calls) == 1
    assert exception_calls[0][1:4] == (1, 3, 3)
    assert (MAP_SUMMARY, 1, 0, 1, 2) in info_calls


def test_map_controller_fails_non_retryable_storage_error_on_first_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeTransactionDb(fail_on_exit=RuntimeError("violates check constraint"))
    controller, _reset_calls = _build_single_map_controller(monkeypatch, db)
    warning_calls = _capture_map_log(monkeypatch, "warning")
    error_calls = _capture_map_log(monkeypatch, "error")
    exception_calls = _capture_map_log(monkeypatch, "exception")
    info_calls = _capture_map_log(monkeypatch, "info")

    controller.run(batch_size=1)

    assert controller.state.failed == [(1, "Failed during database transaction.")]
    assert len(db.cursors) == 1
    assert warning_calls == []
    assert error_calls == []
    assert len(exception_calls) == 1
    assert exception_calls[0][1:4] == (1, 1, 3)
    assert (MAP_SUMMARY, 1, 0, 1, 0) in info_calls
