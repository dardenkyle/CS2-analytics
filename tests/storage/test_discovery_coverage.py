"""Tests for the discovery-coverage queries and gap detection (#125).

fetch_discovery_coverage runs three read-only queries on one cursor, so
a sequenced fake returns one canned result per fetch call;
compute_gap_ranges and align_period_start are pure and tested directly.
"""

import datetime as dt

import cs2_analytics.storage.discovery_coverage as coverage_module
from cs2_analytics.storage.discovery_coverage import (
    align_period_start,
    compute_gap_ranges,
    fetch_discovery_coverage,
)


class _SequencedCursor:
    def __init__(self, results: list[object]) -> None:
        self.results = list(results)
        self.executed: list[tuple[str, tuple | None]] = []

    def __enter__(self) -> "_SequencedCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> object:
        return self.results.pop(0)

    def fetchall(self) -> object:
        return self.results.pop(0)


class _FakeDatabase:
    def __init__(self, cursor: _SequencedCursor) -> None:
        self.cursor = cursor

    def get_cursor(self) -> _SequencedCursor:
        return self.cursor


def test_align_period_start_day_is_identity() -> None:
    day = dt.date(2026, 8, 27)

    assert align_period_start(day, "day") == day


def test_align_period_start_week_aligns_to_monday() -> None:
    thursday = dt.date(2026, 8, 27)

    assert align_period_start(thursday, "week") == dt.date(2026, 8, 24)
    assert align_period_start(dt.date(2026, 8, 24), "week") == dt.date(2026, 8, 24)


def test_compute_gap_ranges_merges_consecutive_missing_days() -> None:
    window_start = dt.date(2026, 8, 1)
    window_end = dt.date(2026, 8, 7)
    counts = [
        (dt.date(2026, 8, 1), 5),
        (dt.date(2026, 8, 4), 2),
        (dt.date(2026, 8, 7), 1),
    ]

    gaps = compute_gap_ranges(window_start, window_end, "day", counts)

    assert gaps == [
        (dt.date(2026, 8, 2), dt.date(2026, 8, 3)),
        (dt.date(2026, 8, 5), dt.date(2026, 8, 6)),
    ]


def test_compute_gap_ranges_reports_trailing_gap() -> None:
    window_start = dt.date(2026, 8, 1)
    window_end = dt.date(2026, 8, 4)
    counts = [(dt.date(2026, 8, 1), 3)]

    gaps = compute_gap_ranges(window_start, window_end, "day", counts)

    assert gaps == [(dt.date(2026, 8, 2), dt.date(2026, 8, 4))]


def test_compute_gap_ranges_empty_window_counts_is_one_gap() -> None:
    window_start = dt.date(2026, 8, 1)
    window_end = dt.date(2026, 8, 3)

    gaps = compute_gap_ranges(window_start, window_end, "day", [])

    assert gaps == [(dt.date(2026, 8, 1), dt.date(2026, 8, 3))]


def test_compute_gap_ranges_full_coverage_has_no_gaps() -> None:
    window_start = dt.date(2026, 8, 1)
    window_end = dt.date(2026, 8, 2)
    counts = [(dt.date(2026, 8, 1), 1), (dt.date(2026, 8, 2), 1)]

    assert compute_gap_ranges(window_start, window_end, "day", counts) == []


def test_compute_gap_ranges_week_buckets_align_with_sql_truncation() -> None:
    # Window opens mid-week; the first bucket is that week's Monday, so a
    # count landing on the Monday bucket covers the opening partial week.
    window_start = dt.date(2026, 8, 27)  # Thursday
    window_end = dt.date(2026, 9, 9)  # Wednesday two weeks on
    counts = [(dt.date(2026, 8, 24), 4)]

    gaps = compute_gap_ranges(window_start, window_end, "week", counts)

    assert gaps == [(dt.date(2026, 8, 31), dt.date(2026, 9, 7))]


def test_fetch_discovery_coverage_combines_three_queries(monkeypatch) -> None:
    earliest = dt.datetime(2025, 10, 2, 12, 0)
    latest = dt.datetime(2026, 8, 30, 20, 0)
    cursor = _SequencedCursor(
        [
            (earliest, latest, 700),
            [(dt.date(2026, 8, 24), 40), (dt.date(2026, 8, 31), 5)],
            [("discovered", 561), ("failed", 2)],
        ]
    )
    monkeypatch.setattr(coverage_module, "get_db", lambda: _FakeDatabase(cursor))

    report = fetch_discovery_coverage(
        dt.date(2025, 10, 1), dt.date(2026, 8, 31), "week"
    )

    assert report["earliest_match"] == earliest
    assert report["latest_match"] == latest
    assert report["total_matches"] == 700
    assert report["window_matches"] == 45
    assert report["period_counts"] == [
        (dt.date(2026, 8, 24), 40),
        (dt.date(2026, 8, 31), 5),
    ]
    assert report["pending_by_status"] == {"discovered": 561, "failed": 2}
    bounds_query, bounds_params = cursor.executed[0]
    period_query, period_params = cursor.executed[1]
    pending_query, _ = cursor.executed[2]
    assert "FROM matches" in bounds_query
    assert bounds_params is None
    assert "date_trunc" in period_query
    # Upper bound is exclusive one day past the window end.
    assert period_params == ("week", dt.date(2025, 10, 1), dt.date(2026, 9, 1))
    assert "FROM match_ingestion_state" in pending_query
    assert "!= 'processed'" in pending_query
