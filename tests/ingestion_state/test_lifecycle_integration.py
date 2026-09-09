"""Integration tests for the ingestion-state lifecycle against a real database.

The contract in docs/ingestion_lifecycle.md (fetch ordering, the mark_as_*
transitions and the timestamps each one sets, failure counting, orphan
release, and requeue guard rails) was previously exercised only through
cursor fakes. These tests run the real SQL on the local test database
provided by the session `test_database` fixture (see tests/conftest.py)
and read rows back with plain queries, so the assertions are independent
of the code under test. Generic behaviour is parametrised over the match
and map managers; the table-specific methods have their own tests. Both
state tables are truncated before every test.
"""

import datetime as dt

import pytest

from cs2_analytics.exceptions import (
    DatabaseOperationError,
    MapIngestionStateError,
    MatchIngestionStateError,
)
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState
from cs2_analytics.ingestion_state.map_ingestion_state import MapIngestionState
from cs2_analytics.ingestion_state.match_ingestion_state import MatchIngestionState

URL = "https://example.test/item/{}"
PARENT_MATCH_ID = 900001


def _url(item_id: int) -> str:
    return URL.format(item_id)


def _row(database, state, item_id: int) -> dict:
    """Read one state row back as a dict, independent of the manager."""
    with database.get_cursor() as cur:
        cur.execute(
            f"SELECT * FROM {state.table_name} WHERE {state.id_field} = %s;",
            (item_id,),
        )
        columns = [column.name for column in cur.description]
        values = cur.fetchone()
    assert values is not None, f"no row {item_id} in {state.table_name}"
    return dict(zip(columns, values, strict=True))


@pytest.fixture()
def clean_state(test_database):
    """Truncate both state tables so each test starts from nothing."""
    with test_database.get_cursor() as cur:
        cur.execute("TRUNCATE match_ingestion_state, map_ingestion_state;")
    return test_database


@pytest.fixture(params=["match", "map"])
def state(request, clean_state):
    """The match or map manager, both pointed at the truncated tables."""
    if request.param == "match":
        return MatchIngestionState()
    return MapIngestionState()


@pytest.fixture()
def parent_match(clean_state):
    """A matches row for map rows that carry match context (FK target)."""
    with clean_state.get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO matches (match_id, match_url, team1, team2, winner, date)
            VALUES (%s, %s, 'team_a', 'team_b', 'team_a', %s)
            ON CONFLICT (match_id) DO NOTHING;
            """,
            (PARENT_MATCH_ID, "https://example.test/parent", dt.datetime(2026, 1, 1)),
        )
    yield PARENT_MATCH_ID
    with clean_state.get_cursor() as cur:
        cur.execute("DELETE FROM matches WHERE match_id = %s;", (PARENT_MATCH_ID,))


# --- queue and fetch -------------------------------------------------------


def test_queue_inserts_a_discovered_row_with_defaults(state, clean_state) -> None:
    state.queue(1, _url(1), source="results", priority=2)

    row = _row(clean_state, state, 1)
    assert row["status"] == "discovered"
    assert row[state.url_field] == _url(1)
    assert row["source"] == "results"
    assert row["priority"] == 2
    assert row["failure_count"] == 0
    assert row["first_seen_at"] is not None
    assert row["last_seen_at"] == row["first_seen_at"]
    assert row["last_attempted_at"] is None


def test_queue_refresh_keeps_first_seen_and_never_lowers_priority(
    state, clean_state
) -> None:
    state.queue(1, _url(1), source="first", priority=5)
    first = _row(clean_state, state, 1)

    state.queue(1, _url(99), source="second", priority=1)
    refreshed = _row(clean_state, state, 1)

    assert refreshed[state.url_field] == _url(99)
    assert refreshed["source"] == "second"
    assert refreshed["priority"] == 5
    assert refreshed["first_seen_at"] == first["first_seen_at"]
    assert refreshed["last_seen_at"] >= first["last_seen_at"]

    state.queue(1, _url(1), priority=9)
    assert _row(clean_state, state, 1)["priority"] == 9


def test_record_many_inserts_a_batch_and_refreshes_on_conflict(
    state, clean_state
) -> None:
    state.record_many([(1, _url(1)), (2, _url(2))], source="batch", priority=1)
    state.record_many([(2, _url(22))], source="batch", priority=0)

    assert _row(clean_state, state, 1)["status"] == "discovered"
    refreshed = _row(clean_state, state, 2)
    assert refreshed[state.url_field] == _url(22)
    assert refreshed["priority"] == 1
    state.record_many([])  # no-op, must not raise


def test_fetch_returns_only_discovered_rows_by_priority_then_first_seen(
    state, clean_state
) -> None:
    state.queue(1, _url(1), priority=0)
    state.queue(2, _url(2), priority=5)
    state.queue(3, _url(3), priority=5)
    state.queue(4, _url(4), priority=9)
    state.mark_as_processed(4)

    assert state.fetch(limit=10) == [(2, _url(2)), (3, _url(3)), (1, _url(1))]
    assert state.fetch(limit=2) == [(2, _url(2)), (3, _url(3))]


# --- transitions -----------------------------------------------------------


def test_mark_as_processing_records_the_attempt(state, clean_state) -> None:
    state.queue(1, _url(1))
    before = _row(clean_state, state, 1)

    state.mark_as_processing(1)

    row = _row(clean_state, state, 1)
    assert row["status"] == "processing"
    assert row["last_attempted_at"] is not None
    assert row["last_updated_at"] >= before["last_updated_at"]
    assert row["last_processed_at"] is None


def test_mark_as_processed_records_completion(state, clean_state) -> None:
    state.queue(1, _url(1))
    state.mark_as_processing(1)

    state.mark_as_processed(1)

    row = _row(clean_state, state, 1)
    assert row["status"] == "processed"
    assert row["last_processed_at"] is not None
    assert row["last_processed_at"] >= row["last_attempted_at"]


def test_mark_as_processed_on_a_caller_cursor_rolls_back_with_the_caller(
    state, clean_state
) -> None:
    state.queue(1, _url(1))

    with pytest.raises(DatabaseOperationError):
        with clean_state.transaction() as cur:
            state.mark_as_processed(1, cur=cur)
            raise RuntimeError("simulated crash after the state write")

    row = _row(clean_state, state, 1)
    assert row["status"] == "discovered"
    assert row["last_processed_at"] is None


def test_mark_as_failed_counts_failures_and_keeps_the_latest_reason(
    state, clean_state
) -> None:
    state.queue(1, _url(1))

    state.mark_as_failed(1, reason="first")
    state.mark_as_failed(1, reason="second")

    row = _row(clean_state, state, 1)
    assert row["status"] == "failed"
    assert row["failure_count"] == 2
    assert row["last_error_message"] == "second"
    assert row["last_failed_at"] is not None


@pytest.mark.parametrize(
    ("method", "expected_status"),
    [("mark_as_dead", "dead"), ("mark_as_skipped", "skipped")],
)
def test_dead_and_skipped_record_a_reason_without_counting_a_failure(
    state, clean_state, method, expected_status
) -> None:
    state.queue(1, _url(1))

    getattr(state, method)(1, reason="operator decision")

    row = _row(clean_state, state, 1)
    assert row["status"] == expected_status
    assert row["last_error_message"] == "operator decision"
    assert row["failure_count"] == 0
    assert row["last_failed_at"] is None


# --- requeue path ----------------------------------------------------------


def test_fetch_requeue_candidates_filters_by_status_id_and_limit(
    state, clean_state
) -> None:
    state.queue(1, _url(1), priority=0)
    state.queue(2, _url(2), priority=5)
    state.queue(3, _url(3))
    state.queue(4, _url(4))
    state.mark_as_failed(1, reason="a")
    state.mark_as_failed(2, reason="b")
    state.mark_as_dead(3, reason="gone")

    assert state.fetch_requeue_candidates("failed") == [(2, 1, "b"), (1, 1, "a")]
    assert state.fetch_requeue_candidates("failed", limit=1) == [(2, 1, "b")]
    assert state.fetch_requeue_candidates("failed", id_value=1) == [(1, 1, "a")]
    assert state.fetch_requeue_candidates("dead") == [(3, 0, "gone")]
    assert state.fetch_requeue_candidates("processing") == []


def test_release_orphaned_processing_resets_only_processing_rows(
    state, clean_state
) -> None:
    state.queue(1, _url(1))
    state.queue(2, _url(2))
    state.queue(3, _url(3))
    state.mark_as_failed(1, reason="earlier attempt")
    state.mark_as_processing(1)
    state.mark_as_processed(2)

    assert state.release_orphaned_processing() == 1

    released = _row(clean_state, state, 1)
    assert released["status"] == "discovered"
    assert released["failure_count"] == 1
    assert released["last_error_message"] == "earlier attempt"
    assert _row(clean_state, state, 2)["status"] == "processed"
    assert _row(clean_state, state, 3)["status"] == "discovered"
    assert state.release_orphaned_processing() == 0


def test_requeue_resets_only_rows_still_in_the_expected_status(
    state, clean_state
) -> None:
    state.queue(1, _url(1))
    state.queue(2, _url(2))
    state.queue(3, _url(3))
    state.mark_as_failed(1, reason="boom")
    state.mark_as_dead(2, reason="gone")
    state.mark_as_processed(3)

    assert state.requeue([1, 2, 3], expected_status="failed") == 1

    requeued = _row(clean_state, state, 1)
    assert requeued["status"] == "discovered"
    assert requeued["failure_count"] == 1
    assert requeued["last_error_message"] == "boom"
    assert _row(clean_state, state, 2)["status"] == "dead"
    assert _row(clean_state, state, 3)["status"] == "processed"
    assert state.requeue([], expected_status="failed") == 0


def test_requeue_then_fail_keeps_counting_from_the_preserved_count(
    state, clean_state
) -> None:
    state.queue(1, _url(1))
    state.mark_as_failed(1, reason="one")
    state.requeue([1], expected_status="failed")

    state.mark_as_failed(1, reason="two")

    assert _row(clean_state, state, 1)["failure_count"] == 2


# --- error wrapping --------------------------------------------------------


def test_database_errors_surface_as_the_manager_error_class(clean_state) -> None:
    broken: BaseIngestionState[int] = BaseIngestionState(
        table_name="no_such_state_table",
        id_field="item_id",
        url_field="item_url",
        error_cls=MapIngestionStateError,
    )

    with pytest.raises(MapIngestionStateError):
        broken.fetch()
    with pytest.raises(MapIngestionStateError):
        broken.mark_as_failed(1, reason="x")
    with pytest.raises(MapIngestionStateError):
        broken.requeue([1], expected_status="failed")


# --- match-specific --------------------------------------------------------


def test_record_discovered_counts_new_rows_and_keeps_dates(clean_state) -> None:
    state = MatchIngestionState()
    first_date = dt.date(2026, 3, 1)

    assert state.record_discovered([(1, _url(1), first_date), (2, _url(2), None)]) == 2
    assert state.record_discovered([(1, _url(1), first_date)]) == 0

    state.record_discovered([(1, _url(1), None)])
    assert _row(clean_state, state, 1)["match_date"] == first_date

    later = dt.date(2026, 3, 5)
    state.record_discovered([(1, _url(1), later), (2, _url(2), dt.date(2026, 2, 1))])
    assert _row(clean_state, state, 1)["match_date"] == later
    assert state.fetch_min_match_date() == dt.date(2026, 2, 1)


def test_fetch_min_match_date_is_none_without_dated_rows(clean_state) -> None:
    state = MatchIngestionState()

    assert state.fetch_min_match_date() is None
    state.record_discovered([(1, _url(1), None)])
    assert state.fetch_min_match_date() is None


def test_mark_as_partial_records_completion_with_partial_status(clean_state) -> None:
    state = MatchIngestionState()
    state.queue(1, _url(1))

    state.mark_as_partial(1)

    row = _row(clean_state, state, 1)
    assert row["status"] == "partial"
    assert row["last_processed_at"] is not None


def test_match_errors_surface_as_the_match_error_class(clean_state) -> None:
    state = MatchIngestionState()

    with pytest.raises(MatchIngestionStateError):
        state.record_discovered([(1, _url(1), "not-a-date")])


# --- map-specific ----------------------------------------------------------


def test_map_queue_keeps_match_context_across_a_contextless_refresh(
    clean_state, parent_match
) -> None:
    state = MapIngestionState()

    state.queue(1, _url(1), match_id=parent_match, map_order=2)
    state.queue(1, _url(11))

    row = _row(clean_state, state, 1)
    assert row["match_id"] == parent_match
    assert row["map_order"] == 2
    assert row["map_url"] == _url(11)
    assert state.fetch_with_match_context(limit=5) == [(1, _url(11), parent_match, 2)]


def test_map_fetch_with_match_context_follows_fetch_ordering(
    clean_state, parent_match
) -> None:
    state = MapIngestionState()
    state.queue(1, _url(1), priority=0, match_id=parent_match, map_order=1)
    state.queue(2, _url(2), priority=3, match_id=parent_match, map_order=2)
    state.mark_as_processed(2)
    state.queue(3, _url(3), priority=3)

    assert state.fetch_with_match_context(limit=5) == [
        (3, _url(3), None, None),
        (1, _url(1), parent_match, 1),
    ]
