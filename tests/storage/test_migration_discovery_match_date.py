"""Round-trip test for migration 20261027_0008.

Runs against the local test database. Seeds processed and pending
ingestion-state rows whose discovery date disagrees with, agrees with,
or is missing against the match's UTC day, runs the upgrade, and checks
that only processed rows that differ are rewritten: a processed row one
day off moves to the match's day, a processed row with no date gains it,
a processed row already equal and a pending row one day off are not
touched. Then downgrades to confirm the values stay and upgrades again
so the shared database is left at head.
"""

import datetime as dt

from alembic import command

from tests.support import alembic_config

PREVIOUS_REVISION = "20261027_0007"

OFF_BY_ONE, EQUAL, UNDATED, PENDING = 9201, 9202, 9203, 9204
MATCH_IDS = (OFF_BY_ONE, EQUAL, UNDATED, PENDING)
MATCH_DAY = dt.date(2026, 7, 11)


def _seed(database) -> None:
    with database.get_cursor() as cur:
        for match_id in MATCH_IDS:
            cur.execute(
                """
                INSERT INTO matches (match_id, match_url, team1, team2, winner, date,
                                     last_scraped_at)
                VALUES (%s, %s, 'A', 'B', 'A', '2026-07-11 02:00:00',
                        '2026-07-20 12:00:00+00');
                """,
                (match_id, f"https://example.test/m/{match_id}"),
            )
        for match_id, status, match_date in (
            (OFF_BY_ONE, "processed", "2026-07-10"),
            (EQUAL, "processed", "2026-07-11"),
            (UNDATED, "processed", None),
            (PENDING, "discovered", "2026-07-10"),
        ):
            cur.execute(
                """
                INSERT INTO match_ingestion_state (match_id, match_url, status,
                                                   match_date)
                VALUES (%s, %s, %s, %s);
                """,
                (match_id, f"https://example.test/m/{match_id}", status, match_date),
            )


def _state_row(database, match_id: int) -> tuple[dt.date | None, int]:
    """The row's discovery date and its row version (xmin).

    xmin changes only when the row is rewritten, so an equal value after
    the migration proves the row was not touched.
    """
    with database.get_cursor() as cur:
        cur.execute(
            "SELECT match_date, xmin::text::bigint FROM match_ingestion_state"
            " WHERE match_id = %s;",
            (match_id,),
        )
        return cur.fetchone()


def _cleanup(database) -> None:
    with database.get_cursor() as cur:
        cur.execute(
            "DELETE FROM match_ingestion_state WHERE match_id = ANY(%s);",
            (list(MATCH_IDS),),
        )
        cur.execute("DELETE FROM matches WHERE match_id = ANY(%s);", (list(MATCH_IDS),))


def test_upgrade_reconciles_only_processed_rows_that_differ(test_database) -> None:
    config = alembic_config()
    try:
        command.downgrade(config, PREVIOUS_REVISION)
        _seed(test_database)
        untouched_before = {
            match_id: _state_row(test_database, match_id)
            for match_id in (EQUAL, PENDING)
        }

        command.upgrade(config, "head")

        assert _state_row(test_database, OFF_BY_ONE)[0] == MATCH_DAY
        assert _state_row(test_database, UNDATED)[0] == MATCH_DAY
        for match_id, before in untouched_before.items():
            assert _state_row(test_database, match_id) == before

        command.downgrade(config, PREVIOUS_REVISION)
        assert _state_row(test_database, OFF_BY_ONE)[0] == MATCH_DAY
    finally:
        _cleanup(test_database)
        command.upgrade(config, "head")
