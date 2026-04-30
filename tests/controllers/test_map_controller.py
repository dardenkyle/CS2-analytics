import pytest

from cs2_analytics.controllers import map_controller as map_module
from cs2_analytics.exceptions import MapParseError, SessionScrapeError


class _FakeMapQueue:
    def __init__(self) -> None:
        self.failed: list[tuple[str, str]] = []
        self.parsed: list[str] = []
        self.processing: list[str] = []

    def fetch(self, limit: int = 25) -> list[tuple[str, str]]:
        return [
            ("map-1", "https://www.hltv.org/stats/matches/mapstatsid/1/test"),
            ("map-2", "https://www.hltv.org/stats/matches/mapstatsid/2/test"),
        ]

    def mark_as_failed(self, item_id: str, reason: str) -> None:
        self.failed.append((item_id, reason))

    def mark_as_parsed(self, item_id: str) -> None:
        self.parsed.append(item_id)

    def mark_as_processing(self, item_id: str) -> None:
        self.processing.append(item_id)


class _SuccessfulScraper:
    def fetch_soup(self, url: str) -> object:
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


class _FailOnceThenSucceedParser:
    def __init__(self) -> None:
        self.calls = 0

    def parse_map(self, soup: object, map_url: str, map_id: str) -> list[object]:
        self.calls += 1
        if self.calls == 1:
            raise MapParseError("No player kills logged.")
        return [object()]


class _SuccessfulParser:
    def parse_map(self, soup: object, map_url: str, map_id: str) -> list[object]:
        return [object()]


def _build_map_controller(
    monkeypatch: pytest.MonkeyPatch,
    scraper_cls: type[object],
    parser_cls: type[object],
) -> map_module.MapController:
    monkeypatch.setattr(map_module, "MapScraper", scraper_cls)
    monkeypatch.setattr(map_module, "MapParser", parser_cls)
    monkeypatch.setattr(map_module, "MapIngestionState", _FakeMapQueue)
    monkeypatch.setattr(
        map_module,
        "store_players",
        lambda players: None,
    )
    monkeypatch.setattr(map_module.time, "sleep", lambda *_args, **_kwargs: None)
    return map_module.MapController()


def test_map_controller_continues_after_item_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored_players: list[list[object]] = []
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(map_module, "MapScraper", _SuccessfulScraper)
    monkeypatch.setattr(map_module, "MapParser", _FailOnceThenSucceedParser)
    monkeypatch.setattr(map_module, "MapIngestionState", _FakeMapQueue)
    monkeypatch.setattr(
        map_module,
        "store_players",
        lambda players: stored_players.append(players),
    )
    monkeypatch.setattr(map_module.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        map_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )

    controller = map_module.MapController()
    controller.run(batch_size=2)

    assert controller.queue.failed == [("map-1", "No player kills logged.")]
    assert controller.queue.parsed == ["map-2"]
    assert controller.queue.processing == ["map-1", "map-2"]
    assert len(stored_players) == 1
    assert any(
        call_args[0]
        == "MapController summary: queued=%d succeeded=%d failed=%d retries=%d"
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
    monkeypatch.setattr(
        map_module,
        "store_players",
        lambda players: stored_players.append(players),
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
        controller.queue,
        "fetch",
        lambda limit=25: [("map-1", "https://www.hltv.org/stats/matches/mapstatsid/1/test")],
    )

    controller.run(batch_size=1)

    assert controller.queue.failed == []
    assert controller.queue.parsed == ["map-1"]
    assert len(stored_players) == 1
    assert len(reset_calls) == 1
    assert any(
        call_args[0]
        == "MapController summary: queued=%d succeeded=%d failed=%d retries=%d"
        and call_args[1:] == (1, 1, 0, 1)
        for call_args, _ in info_calls
    )


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
        controller.queue,
        "fetch",
        lambda limit=25: [("map-1", "https://www.hltv.org/stats/matches/mapstatsid/1/test")],
    )

    controller.run(batch_size=1)

    assert controller.queue.failed == [
        ("map-1", "Failed to fetch map stats page: https://www.hltv.org/stats/matches/mapstatsid/1/test")
    ]
    assert controller.queue.parsed == []
    assert len(reset_calls) == 2
    assert error_calls == [
        (
            (
                "Exhausted retries for map %s after %d attempts; marking failed and continuing.",
                "map-1",
                3,
            ),
            {},
        )
    ]
    assert len(exception_calls) == 1
    assert any(
        call_args[0]
        == "MapController summary: queued=%d succeeded=%d failed=%d retries=%d"
        and call_args[1:] == (1, 0, 1, 2)
        for call_args, _ in info_calls
    )
