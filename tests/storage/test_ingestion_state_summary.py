"""Tests for the failure-detail queries in ingestion_state_summary (#123).

The helpers format table/column names from module constants and
parametrize runtime values, so these tests assert the emitted SQL targets
the right table and id column, passes (status, limit) as parameters, and
returns cursor rows unchanged. The database is faked; no connection is
opened.
"""

import pytest

import cs2_analytics.storage.ingestion_state_summary as summary_module
from cs2_analytics.storage.ingestion_state_summary import (
    fetch_failure_groups,
    fetch_failure_rows,
)


class _RecordingCursor:
    def __init__(self, rows: list[tuple]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self) -> "_RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[tuple]:
        return self.rows


class _FakeDatabase:
    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor = cursor

    def get_cursor(self) -> _RecordingCursor:
        return self.cursor


def _install_fake_db(monkeypatch, rows: list[tuple]) -> _RecordingCursor:
    cursor = _RecordingCursor(rows)
    monkeypatch.setattr(summary_module, "get_db", lambda: _FakeDatabase(cursor))
    return cursor


@pytest.mark.parametrize(
    ("stage", "table", "id_column"),
    [
        ("match", "match_ingestion_state", "match_id"),
        ("map", "map_ingestion_state", "map_id"),
    ],
)
def test_fetch_failure_rows_targets_stage_table(
    monkeypatch, stage, table, id_column
) -> None:
    expected = [(1, "failed", 2, None, "boom")]
    cursor = _install_fake_db(monkeypatch, expected)

    rows = fetch_failure_rows(stage, "failed", 20)

    assert rows == expected
    query, params = cursor.executed[0]
    assert f"FROM {table}" in query
    assert f"SELECT {id_column}" in query
    assert f"ORDER BY last_failed_at DESC NULLS LAST, {id_column}" in query
    assert params == ("failed", 20)


def test_fetch_failure_rows_parametrizes_status_and_limit(monkeypatch) -> None:
    cursor = _install_fake_db(monkeypatch, [])

    fetch_failure_rows("match", "dead", 5)

    query, params = cursor.executed[0]
    assert "dead" not in query
    assert params == ("dead", 5)


def test_fetch_failure_groups_aggregates_by_error_message(monkeypatch) -> None:
    expected = [("boom", 4, None), (None, 1, None)]
    cursor = _install_fake_db(monkeypatch, expected)

    groups = fetch_failure_groups("map", "failed", 10)

    assert groups == expected
    query, params = cursor.executed[0]
    assert "FROM map_ingestion_state" in query
    assert "GROUP BY last_error_message" in query
    assert "ORDER BY COUNT(*) DESC" in query
    assert params == ("failed", 10)
