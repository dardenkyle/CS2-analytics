from cs2_analytics.stage_services import MapStageService


class _FakeScraper:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch_soup(self, url: str) -> object:
        self.urls.append(url)
        return object()


class _FakeParser:
    def __init__(self, players: list[object]) -> None:
        self.players = players
        self.calls: list[tuple[str, str]] = []

    def parse_map(self, _soup: object, map_url: str, map_id: str) -> list[object]:
        self.calls.append((map_url, map_id))
        return self.players


class _FakeMapState:
    def __init__(self) -> None:
        self.processing: list[str] = []
        self.processed: list[str] = []
        self.failed: list[tuple[str, str]] = []

    def mark_as_processing(self, item_id: str) -> None:
        self.processing.append(item_id)

    def mark_as_processed(self, item_id: str) -> None:
        self.processed.append(item_id)

    def mark_as_failed(self, item_id: str, reason: str) -> None:
        self.failed.append((item_id, reason))


def test_map_stage_service_processes_success() -> None:
    stored_players: list[list[object]] = []
    players = [object()]
    map_state = _FakeMapState()
    parser = _FakeParser(players=players)
    service = MapStageService(
        parser=parser,
        store_players=lambda parsed_players: stored_players.append(parsed_players),
        map_state=map_state,
    )

    result = service.process_item(
        "map-1",
        "https://www.hltv.org/stats/matches/mapstatsid/1/test",
        scraper=_FakeScraper(),
    )

    assert result.succeeded is True
    assert result.status == "processed"
    assert parser.calls == [
        ("https://www.hltv.org/stats/matches/mapstatsid/1/test", "map-1")
    ]
    assert map_state.processing == []
    assert map_state.processed == ["map-1"]
    assert map_state.failed == []
    assert stored_players == [players]


def test_map_stage_service_marks_failed_when_parser_returns_no_players() -> None:
    stored_players: list[list[object]] = []
    map_state = _FakeMapState()
    service = MapStageService(
        parser=_FakeParser(players=[]),
        store_players=lambda parsed_players: stored_players.append(parsed_players),
        map_state=map_state,
    )

    result = service.process_item(
        "map-1",
        "https://www.hltv.org/stats/matches/mapstatsid/1/test",
        scraper=_FakeScraper(),
    )

    assert result.succeeded is False
    assert result.status == "failed"
    assert result.message == "Parsing returned no player records"
    assert map_state.processing == []
    assert map_state.processed == []
    assert map_state.failed == [("map-1", "Parsing returned no player records")]
    assert stored_players == []


def test_map_stage_service_processes_with_attempt_scraper() -> None:
    attempt_scraper = _FakeScraper()
    service = MapStageService(
        parser=_FakeParser(players=[object()]),
        store_players=lambda _players: None,
        map_state=_FakeMapState(),
    )

    service.process_item(
        "map-1",
        "https://www.hltv.org/stats/matches/mapstatsid/1/test",
        scraper=attempt_scraper,
    )

    assert attempt_scraper.urls == [
        "https://www.hltv.org/stats/matches/mapstatsid/1/test"
    ]
