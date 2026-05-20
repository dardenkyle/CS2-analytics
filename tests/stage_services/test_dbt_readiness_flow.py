from dataclasses import dataclass
from datetime import UTC, datetime

from cs2_analytics.models.map import Map
from cs2_analytics.models.match import Match
from cs2_analytics.models.player import Player
from cs2_analytics.stage_services import MapStageService, MatchStageService


@dataclass(frozen=True)
class _ParsedMap:
    map: Map
    players: list[Player]


@dataclass(frozen=True)
class _MapIngestionRecord:
    map_id: int
    map_url: str
    source: str
    match_id: int | None
    map_order: int | None


class _FakeScraper:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch_soup(self, url: str) -> object:
        self.urls.append(url)
        return object()


class _FakeMatchParser:
    def __init__(self, match: Match) -> None:
        self.match = match

    def parse_match(
        self, _soup: object, _match_url: str
    ) -> tuple[Match, list[tuple[int, str]], list[tuple[str, str]]]:
        return self.match, self.match.map_links, self.match.demo_links


class _FakeMapParser:
    def parse_map_details(
        self,
        _soup: object,
        map_url: str,
        map_id: int,
        *,
        match_id: int | None,
        map_order: int | None,
    ) -> _ParsedMap:
        assert match_id is not None
        assert map_order is not None

        now = datetime.now(UTC)
        map_name = f"Map {map_order}"
        parsed_map = Map(
            map_id=map_id,
            match_id=match_id,
            map_url=map_url,
            map_name=map_name,
            map_order=map_order,
            team1_score=13,
            team2_score=9,
            map_winner="NAVI",
            date="2026-05-20 12:00:00",
            inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )
        players = [
            _player(map_id, 1000 + map_id, "NAVI", map_name, now),
            _player(map_id, 2000 + map_id, "Vitality", map_name, now),
        ]
        return _ParsedMap(map=parsed_map, players=players)


class _FakeMatchState:
    def __init__(self) -> None:
        self.processed: list[int] = []
        self.failed: list[tuple[int, str]] = []

    def mark_as_processed(self, item_id: int) -> None:
        self.processed.append(item_id)

    def mark_as_failed(self, item_id: int, reason: str) -> None:
        self.failed.append((item_id, reason))


class _FakeMapState:
    def __init__(self) -> None:
        self.records: list[_MapIngestionRecord] = []
        self.processed: list[int] = []
        self.failed: list[tuple[int, str]] = []

    def queue(
        self,
        item_id: int,
        url: str,
        source: str = "unknown",
        priority: int = 0,
        match_id: int | None = None,
        map_order: int | None = None,
    ) -> None:
        del priority
        self.records.append(
            _MapIngestionRecord(
                map_id=item_id,
                map_url=url,
                source=source,
                match_id=match_id,
                map_order=map_order,
            )
        )

    def mark_as_processed(self, item_id: int) -> None:
        self.processed.append(item_id)

    def mark_as_failed(self, item_id: int, reason: str) -> None:
        self.failed.append((item_id, reason))


class _FakeDemoState:
    def queue(
        self,
        item_id: str,
        url: str,
        source: str = "unknown",
        priority: int = 0,
    ) -> None:
        del item_id, url, source, priority


def _match() -> Match:
    now = datetime.now(UTC)
    return Match(
        match_id=700001,
        match_url="https://www.hltv.org/matches/700001/navi-vs-vitality",
        map_links=[
            (
                800001,
                "https://www.hltv.org/stats/matches/mapstatsid/800001/navi-vs-vitality",
            ),
            (
                800002,
                "https://www.hltv.org/stats/matches/mapstatsid/800002/navi-vs-vitality",
            ),
        ],
        demo_links=[],
        team1="NAVI",
        team2="Vitality",
        score1=2,
        score2=0,
        winner="NAVI",
        event="Test Finals",
        match_type="BO3",
        forfeit=False,
        date="2026-05-20 12:00:00",
        last_inserted_at=now,
        last_scraped_at=now,
        last_updated_at=now,
        data_complete=True,
    )


def _player(
    map_id: int, player_id: int, team_name: str, map_name: str, now: datetime
) -> Player:
    return Player(
        map_id=map_id,
        player_id=player_id,
        player_name=f"Player {player_id}",
        player_url=f"https://www.hltv.org/player/{player_id}/player-{player_id}",
        map_name=map_name,
        team_name=team_name,
        kills=20,
        headshots=10,
        assists=5,
        flash_assists=1,
        deaths=14,
        traded_deaths=2,
        opening_kills=3,
        opening_deaths=1,
        multi_kills=4,
        clutches_won=1,
        kast=78.6,
        kd_diff=6,
        adr=84.2,
        fk_diff=2,
        round_swing=1.5,
        rating=1.22,
        last_inserted_at=now,
        last_scraped_at=now,
        last_updated_at=now,
        data_complete=True,
    )


def test_match_to_map_to_player_flow_has_stable_dbt_ready_grains() -> None:
    match = _match()
    match_state = _FakeMatchState()
    map_state = _FakeMapState()
    stored_matches: list[Match] = []
    stored_maps: list[Map] = []
    stored_players: list[Player] = []

    match_service = MatchStageService(
        parser=_FakeMatchParser(match),
        store_matches=stored_matches.extend,
        match_state=match_state,
        map_state=map_state,
        demo_state=_FakeDemoState(),
    )

    match_result = match_service.process_item(
        match.match_id,
        match.match_url,
        scraper=_FakeScraper(),
    )

    assert match_result.succeeded is True
    assert match_state.processed == [match.match_id]
    assert match_state.failed == []
    assert [stored.match_id for stored in stored_matches] == [match.match_id]
    assert [
        (record.map_id, record.match_id, record.map_order, record.source)
        for record in map_state.records
    ] == [
        (800001, match.match_id, 1, "match_parser"),
        (800002, match.match_id, 2, "match_parser"),
    ]

    map_service = MapStageService(
        parser=_FakeMapParser(),
        store_maps=stored_maps.extend,
        store_players=stored_players.extend,
        map_state=map_state,
    )

    for record in map_state.records:
        map_result = map_service.process_item(
            record.map_id,
            record.map_url,
            scraper=_FakeScraper(),
            match_id=record.match_id,
            map_order=record.map_order,
        )

        assert map_result.succeeded is True

    match_grain = {stored_match.match_id for stored_match in stored_matches}
    map_grain = {stored_map.map_id for stored_map in stored_maps}
    player_grain = {
        (stored_player.map_id, stored_player.player_id)
        for stored_player in stored_players
    }

    assert len(stored_matches) == len(match_grain) == 1
    assert len(stored_maps) == len(map_grain) == 2
    assert len(stored_players) == len(player_grain) == 4
    assert {stored_map.match_id for stored_map in stored_maps} == match_grain
    assert {stored_map.map_order for stored_map in stored_maps} == {1, 2}
    assert {stored_player.map_id for stored_player in stored_players} == map_grain
    assert map_state.processed == [800001, 800002]
    assert map_state.failed == []

    maps_by_id = {stored_map.map_id: stored_map for stored_map in stored_maps}
    matches_by_id = {
        stored_match.match_id: stored_match for stored_match in stored_matches
    }
    joined_rows = [
        (
            player.player_id,
            player.map_id,
            maps_by_id[player.map_id].match_id,
            matches_by_id[maps_by_id[player.map_id].match_id].winner,
        )
        for player in stored_players
    ]

    assert len(joined_rows) == 4
    assert {row[2] for row in joined_rows} == {match.match_id}
    assert {row[3] for row in joined_rows} == {"NAVI"}
