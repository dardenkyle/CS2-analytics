from dataclasses import dataclass

from cs2_analytics.stage_services import MapStageService
from tests.support import FakeTransactionDb


@dataclass(frozen=True)
class _ParsedMap:
    map: object
    players: list[object]


class _FakeScraper:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch_soup(self, url: str) -> object:
        self.urls.append(url)
        return object()


class _FakeParser:
    def __init__(self, players: list[object], map_obj: object | None = None) -> None:
        self.players = players
        self.map_obj = map_obj or object()
        self.calls: list[tuple[str, int, int | None, int | None]] = []

    def parse_map_details(
        self,
        _soup: object,
        map_url: str,
        map_id: int,
        *,
        match_id: int | None,
        map_order: int | None,
    ) -> _ParsedMap:
        self.calls.append((map_url, map_id, match_id, map_order))
        return _ParsedMap(map=self.map_obj, players=self.players)


class _FakeMapState:
    def __init__(self) -> None:
        self.processing: list[int] = []
        self.processed: list[int] = []
        self.failed: list[tuple[int, str]] = []

    def mark_as_processing(self, item_id: int) -> None:
        self.processing.append(item_id)

    def mark_as_processed(self, item_id: int, cur=None) -> None:
        self.processed.append(item_id)

    def mark_as_failed(self, item_id: int, reason: str) -> None:
        self.failed.append((item_id, reason))


def test_map_stage_service_processes_success() -> None:
    stored_maps: list[list[object]] = []
    stored_players: list[list[object]] = []
    parsed_map = object()
    players = [object()]
    map_state = _FakeMapState()
    parser = _FakeParser(players=players, map_obj=parsed_map)
    service = MapStageService(
        parser=parser,
        store_maps=lambda maps, cur=None: stored_maps.append(maps),
        store_players=lambda parsed_players, cur=None: stored_players.append(
            parsed_players
        ),
        map_state=map_state,
        db=FakeTransactionDb(),
    )

    result = service.process_item(
        1,
        "https://www.hltv.org/stats/matches/mapstatsid/1/test",
        scraper=_FakeScraper(),
        match_id=101,
        map_order=1,
    )

    assert result.succeeded is True
    assert result.status == "processed"
    assert parser.calls == [
        ("https://www.hltv.org/stats/matches/mapstatsid/1/test", 1, 101, 1)
    ]
    assert map_state.processing == []
    assert map_state.processed == [1]
    assert map_state.failed == []
    assert stored_maps == [[parsed_map]]
    assert stored_players == [players]


def test_map_stage_service_marks_failed_when_parser_returns_no_players() -> None:
    stored_maps: list[list[object]] = []
    stored_players: list[list[object]] = []
    map_state = _FakeMapState()
    service = MapStageService(
        parser=_FakeParser(players=[]),
        store_maps=lambda maps, cur=None: stored_maps.append(maps),
        store_players=lambda parsed_players, cur=None: stored_players.append(
            parsed_players
        ),
        map_state=map_state,
        db=FakeTransactionDb(),
    )

    result = service.process_item(
        1,
        "https://www.hltv.org/stats/matches/mapstatsid/1/test",
        scraper=_FakeScraper(),
        match_id=101,
        map_order=1,
    )

    assert result.succeeded is False
    assert result.status == "failed"
    assert result.message == "Parsing returned no player records"
    assert map_state.processing == []
    assert map_state.processed == []
    assert map_state.failed == [(1, "Parsing returned no player records")]
    assert stored_maps == []
    assert stored_players == []


def test_map_stage_service_processes_with_attempt_scraper() -> None:
    attempt_scraper = _FakeScraper()
    service = MapStageService(
        parser=_FakeParser(players=[object()]),
        store_maps=lambda _maps, cur=None: None,
        store_players=lambda _players, cur=None: None,
        map_state=_FakeMapState(),
        db=FakeTransactionDb(),
    )

    service.process_item(
        1,
        "https://www.hltv.org/stats/matches/mapstatsid/1/test",
        scraper=attempt_scraper,
        match_id=101,
        map_order=1,
    )

    assert attempt_scraper.urls == [
        "https://www.hltv.org/stats/matches/mapstatsid/1/test"
    ]
