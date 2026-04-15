import pytest

from cs2_analytics.controllers import map_controller as map_module
from cs2_analytics.exceptions import MapParseError


class _FakeMapQueue:
    def __init__(self) -> None:
        self.failed: list[tuple[str, str]] = []
        self.parsed: list[str] = []

    def fetch(self, limit: int = 25) -> list[tuple[str, str]]:
        return [
            ("map-1", "https://www.hltv.org/stats/matches/mapstatsid/1/test"),
            ("map-2", "https://www.hltv.org/stats/matches/mapstatsid/2/test"),
        ]

    def mark_as_failed(self, item_id: str, reason: str) -> None:
        self.failed.append((item_id, reason))

    def mark_as_parsed(self, item_id: str) -> None:
        self.parsed.append(item_id)


class _SuccessfulScraper:
    def fetch_soup(self, url: str) -> object:
        return object()

    def close(self) -> None:
        return None


class _FailOnceThenSucceedParser:
    def __init__(self) -> None:
        self.calls = 0

    def parse_map(self, soup: object, map_url: str, map_id: str) -> list[object]:
        self.calls += 1
        if self.calls == 1:
            raise MapParseError("No player kills logged.")
        return [object()]


def test_map_controller_continues_after_item_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored_players: list[list[object]] = []
    monkeypatch.setattr(map_module, "MapScraper", _SuccessfulScraper)
    monkeypatch.setattr(map_module, "MapParser", _FailOnceThenSucceedParser)
    monkeypatch.setattr(map_module, "MapScrapeQueue", _FakeMapQueue)
    monkeypatch.setattr(
        map_module,
        "store_players",
        lambda players: stored_players.append(players),
    )
    monkeypatch.setattr(map_module.time, "sleep", lambda *_args, **_kwargs: None)

    controller = map_module.MapController()
    controller.run(batch_size=2)

    assert controller.queue.failed == [("map-1", "No player kills logged.")]
    assert controller.queue.parsed == ["map-2"]
    assert len(stored_players) == 1
