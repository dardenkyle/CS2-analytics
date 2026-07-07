"""Tests for atomic data-write plus state-transition behavior (ADR-0013).

Unit tests prove the wiring: every write in a stage item shares one
transaction cursor. The integration test proves the guarantee against a real
PostgreSQL database: a failure between the data write and the processed mark
rolls back the data write.
"""

import datetime as dt

import pytest

from cs2_analytics.exceptions import DatabaseOperationError
from cs2_analytics.stage_services import MapStageService, MatchStageService
from tests.support import FakeTransactionDb


class _FakeScraper:
    def fetch_soup(self, _url: str) -> object:
        return object()


class _RecordingState:
    """Fake ingestion state capturing which cursor each call received."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def mark_as_processed(self, item_id, cur=None) -> None:
        self.calls.append(("mark_as_processed", cur))

    def mark_as_failed(self, item_id, reason="unknown", cur=None) -> None:
        self.calls.append(("mark_as_failed", cur))

    def queue(self, *args, cur=None, **kwargs) -> None:
        self.calls.append(("queue", cur))


class _MatchParser:
    def __init__(self, map_links, demo_links) -> None:
        self.map_links = map_links
        self.demo_links = demo_links

    def parse_match(self, _soup, _url):
        return object(), self.map_links, self.demo_links


class _MapParser:
    def parse_map_details(self, _soup, _url, _map_id, *, match_id, map_order):
        class _Parsed:
            map = object()
            players = [object()]

        return _Parsed()


def test_match_stage_writes_share_one_transaction_cursor() -> None:
    db = FakeTransactionDb()
    match_state = _RecordingState()
    map_state = _RecordingState()
    demo_state = _RecordingState()
    store_cursors: list[object] = []

    service = MatchStageService(
        parser=_MatchParser(
            map_links=[(1, "https://example.test/map/1")],
            demo_links=[("d1", "https://example.test/demo/1")],
        ),
        store_matches=lambda _matches, cur=None: store_cursors.append(cur),
        match_state=match_state,
        map_state=map_state,
        demo_state=demo_state,
        db=db,
    )

    result = service.process_item(
        1, "https://example.test/match/1", scraper=_FakeScraper()
    )

    assert result.succeeded is True
    assert len(db.cursors) == 1
    shared = db.cursors[0]
    assert store_cursors == [shared]
    assert map_state.calls == [("queue", shared)]
    assert demo_state.calls == [("queue", shared)]
    assert match_state.calls == [("mark_as_processed", shared)]


def test_map_stage_writes_share_one_transaction_cursor() -> None:
    db = FakeTransactionDb()
    map_state = _RecordingState()
    store_cursors: list[object] = []

    service = MapStageService(
        parser=_MapParser(),
        store_maps=lambda _maps, cur=None: store_cursors.append(cur),
        store_players=lambda _players, cur=None: store_cursors.append(cur),
        map_state=map_state,
        db=db,
    )

    result = service.process_item(
        1, "https://example.test/map/1", scraper=_FakeScraper(), match_id=2, map_order=1
    )

    assert result.succeeded is True
    assert len(db.cursors) == 1
    shared = db.cursors[0]
    assert store_cursors == [shared, shared]
    assert map_state.calls == [("mark_as_processed", shared)]


class TestAtomicRollbackIntegration:
    """Acceptance test against a real database: no half-committed rows."""

    PARENT_MATCH_ID = 990000
    MAP_ID = 990001

    @pytest.fixture()
    def db(self):
        from cs2_analytics.storage.db_instance import get_db

        try:
            database = get_db()
        except Exception:
            pytest.skip("PostgreSQL is not available for integration tests")

        with database.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO matches (match_id, match_url, team1, team2, winner, date)
                VALUES (%s, %s, 'team_a', 'team_b', 'team_a', %s)
                ON CONFLICT (match_id) DO NOTHING;
                """,
                (
                    self.PARENT_MATCH_ID,
                    "https://example.test/atomicity-parent",
                    dt.datetime(2026, 1, 1),
                ),
            )
        yield database
        with database.get_cursor() as cur:
            # Deleting the parent match cascades to the maps row if it leaked.
            cur.execute(
                "DELETE FROM matches WHERE match_id = %s;", (self.PARENT_MATCH_ID,)
            )

    def test_failure_after_data_write_rolls_back_the_data_write(self, db) -> None:
        from cs2_analytics.storage.map_storage import store_maps

        class _Map:
            map_id = TestAtomicRollbackIntegration.MAP_ID
            match_id = TestAtomicRollbackIntegration.PARENT_MATCH_ID
            map_url = "https://example.test/atomicity"
            map_order = 1
            map_name = "test_atomicity"
            team1_score = 1
            team2_score = 2
            map_winner = "team2"
            date = dt.date(2026, 1, 1)
            inserted_at = dt.datetime(2026, 1, 1)
            last_scraped_at = dt.datetime(2026, 1, 1)
            last_updated_at = dt.datetime(2026, 1, 1)
            data_complete = True

        boom = RuntimeError("simulated crash between data write and state mark")

        with pytest.raises(DatabaseOperationError) as exc_info:
            with db.transaction() as cur:
                store_maps([_Map()], cur=cur)
                raise boom

        assert exc_info.value.__cause__ is boom

        with db.get_cursor() as cur:
            cur.execute("SELECT map_id FROM maps WHERE map_id = %s;", (self.MAP_ID,))
            assert cur.fetchall() == [], (
                "data write survived a failed transaction; atomicity is broken"
            )
