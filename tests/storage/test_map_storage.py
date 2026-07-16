from datetime import UTC, datetime

import pytest

from cs2_analytics.exceptions import MapStorageError
from cs2_analytics.models.map import Map
from cs2_analytics.storage import map_storage as map_storage_module


class _RecordingCursor:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.executed: list[tuple[str, list[dict[str, object]]]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def executemany(self, query: str, values: list[dict[str, object]]) -> None:
        if self.should_fail:
            raise RuntimeError("insert failed")
        self.executed.append((query, values))


class _FakeDb:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor = cursor

    def get_cursor(self) -> _RecordingCursor:
        return self.cursor


def _map() -> Map:
    now = datetime.now(UTC)
    return Map(
        map_id=204269,
        match_id=1001,
        map_url="https://www.hltv.org/stats/matches/mapstatsid/204269/test",
        map_name="Train",
        map_order=1,
        team1_score=26,
        team2_score=28,
        map_winner="Liquid",
        date="2025-08-05 14:30:00",
        inserted_at=now,
        last_scraped_at=now,
        last_updated_at=now,
        data_complete=True,
    )


def _conflict_update_clause(query: str) -> str:
    assert "ON CONFLICT" in query, (
        "Expected storage query to define an upsert conflict clause."
    )
    return query.split("ON CONFLICT", maxsplit=1)[1]


def test_store_maps_writes_active_map_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(map_storage_module, "get_db", lambda: _FakeDb(cursor))

    map_storage_module.store_maps([_map()])

    query, values = cursor.executed[0]
    params = values[0]
    assert "map_url" in query
    assert "map_order" in query
    assert "map_winner" in query
    assert "inserted_at" in query
    assert params["map_id"] == 204269
    assert params["match_id"] == 1001
    assert params["map_order"] == 1
    assert params["map_winner"] == "Liquid"


def test_store_maps_batches_rows_into_one_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(map_storage_module, "get_db", lambda: _FakeDb(cursor))

    map_storage_module.store_maps([_map(), _map()])

    assert len(cursor.executed) == 1
    _query, values = cursor.executed[0]
    assert len(values) == 2


def test_store_maps_refreshes_trusted_fields_without_replacing_inserted_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = _RecordingCursor()
    monkeypatch.setattr(map_storage_module, "get_db", lambda: _FakeDb(cursor))

    map_storage_module.store_maps([_map()])

    query, _values = cursor.executed[0]
    conflict_update = _conflict_update_clause(query)

    for field_name in (
        "match_id",
        "map_url",
        "map_order",
        "map_name",
        "team1_score",
        "team2_score",
        "map_winner",
        "date",
        "last_scraped_at",
        "last_updated_at",
        "data_complete",
    ):
        assert f"{field_name} = EXCLUDED.{field_name}" in conflict_update

    assert "inserted_at = EXCLUDED.inserted_at" not in conflict_update


def test_store_maps_wraps_database_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = _RecordingCursor(should_fail=True)
    monkeypatch.setattr(map_storage_module, "get_db", lambda: _FakeDb(cursor))

    with pytest.raises(MapStorageError, match="Failed to store map records."):
        map_storage_module.store_maps([_map()])


def test_store_maps_wraps_database_factory_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_database_error():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(map_storage_module, "get_db", raise_database_error)

    with pytest.raises(MapStorageError, match="Failed to store map records."):
        map_storage_module.store_maps([_map()])
