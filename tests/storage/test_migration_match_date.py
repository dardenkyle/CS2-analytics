"""Round-trip test for migration 20261027_0007.

Runs against the local test database. Seeds matches at midnight the way
the old match parser wrote them, with maps carrying the UTC instant the
map parser has always written (the source stamps every map of a match
with the match's start), runs the upgrade, and checks that a match whose
day disagreed with its maps moves to that instant, a match on the right
day gains the time of day, a fallback-parsed midnight map is ignored, a
match with no usable map is left alone, and a match already equal to its
maps is not rewritten at all. Rewritten rows get a fresh
`last_updated_at` so the incremental mart picks them up; untouched rows
keep theirs. Then downgrades to confirm the midnight rendering and
upgrades again so the shared database is left at head.
"""

import datetime as dt

from alembic import command

from tests.support import alembic_config

PREVIOUS_REVISION = "20260923_0006"

WRONG_DAY_MATCH, SAME_DAY_MATCH, NO_MAP_MATCH = 9101, 9102, 9103
EXACT_MATCH, FALLBACK_ONLY_MATCH = 9104, 9105
MATCH_IDS = (
    WRONG_DAY_MATCH,
    SAME_DAY_MATCH,
    NO_MAP_MATCH,
    EXACT_MATCH,
    FALLBACK_ONLY_MATCH,
)
MAP_IDS = (8101, 8102, 8103, 8104, 8105, 8106)
SEEDED_UPDATED_AT = dt.datetime(2026, 7, 20, 12, 0, 0, tzinfo=dt.UTC)


def _seed(database) -> None:
    """Insert midnight match dates and UTC map instants as production holds them."""
    with database.get_cursor() as cur:
        for match_id, date in (
            # Started 9 PM Central on the 10th, which is 02:00 UTC on the
            # 11th; the desktop wrote the Central day.
            (WRONG_DAY_MATCH, "2026-07-10 00:00:00"),
            (SAME_DAY_MATCH, "2026-07-12 00:00:00"),
            (NO_MAP_MATCH, "2026-07-13 00:00:00"),
            (EXACT_MATCH, "2026-07-14 15:00:00"),
            (FALLBACK_ONLY_MATCH, "2026-07-15 00:00:00"),
        ):
            cur.execute(
                """
                INSERT INTO matches (match_id, match_url, team1, team2, winner, date,
                                     last_scraped_at, last_updated_at)
                VALUES (%s, %s, 'A', 'B', 'A', %s, %s, %s);
                """,
                (
                    match_id,
                    f"https://example.test/m/{match_id}",
                    date,
                    SEEDED_UPDATED_AT,
                    SEEDED_UPDATED_AT,
                ),
            )
        for map_id, match_id, map_order, date in (
            # Both maps carry the match's start; the third was parsed
            # through the text fallback and sits at midnight.
            (MAP_IDS[0], WRONG_DAY_MATCH, 1, "2026-07-11 02:00:00"),
            (MAP_IDS[1], WRONG_DAY_MATCH, 2, "2026-07-11 02:00:00"),
            (MAP_IDS[2], WRONG_DAY_MATCH, 3, "2026-07-11 00:00:00"),
            (MAP_IDS[3], SAME_DAY_MATCH, 1, "2026-07-12 18:00:00"),
            (MAP_IDS[4], EXACT_MATCH, 1, "2026-07-14 15:00:00"),
            (MAP_IDS[5], FALLBACK_ONLY_MATCH, 1, "2026-07-16 00:00:00"),
        ):
            cur.execute(
                """
                INSERT INTO maps (map_id, match_id, map_url, map_order, map_name,
                                  team1_score, team2_score, map_winner, date,
                                  last_scraped_at)
                VALUES (%s, %s, %s, %s, 'de_test', 13, 7, 'A', %s, %s);
                """,
                (
                    map_id,
                    match_id,
                    f"https://example.test/p/{map_id}",
                    map_order,
                    date,
                    SEEDED_UPDATED_AT,
                ),
            )


def _match_row(database, match_id: int) -> tuple[dt.datetime, dt.datetime, int]:
    """The match's date, last_updated_at, and row version (xmin).

    xmin changes only when the row is rewritten, so an equal value after
    the migration proves the row was not touched.
    """
    with database.get_cursor() as cur:
        cur.execute(
            "SELECT date, last_updated_at, xmin::text::bigint FROM matches"
            " WHERE match_id = %s;",
            (match_id,),
        )
        return cur.fetchone()


def _cleanup(database) -> None:
    with database.get_cursor() as cur:
        cur.execute("DELETE FROM maps WHERE map_id = ANY(%s);", (list(MAP_IDS),))
        cur.execute("DELETE FROM matches WHERE match_id = ANY(%s);", (list(MATCH_IDS),))


def test_upgrade_sets_match_date_from_its_maps_and_leaves_the_rest(
    test_database,
) -> None:
    config = alembic_config()
    try:
        command.downgrade(config, PREVIOUS_REVISION)
        _seed(test_database)
        untouched_before = {
            match_id: _match_row(test_database, match_id)
            for match_id in (NO_MAP_MATCH, EXACT_MATCH, FALLBACK_ONLY_MATCH)
        }

        command.upgrade(config, "head")

        for match_id, expected in (
            (WRONG_DAY_MATCH, dt.datetime(2026, 7, 11, 2, 0, 0)),
            (SAME_DAY_MATCH, dt.datetime(2026, 7, 12, 18, 0, 0)),
        ):
            date, updated_at, _ = _match_row(test_database, match_id)
            assert date == expected
            assert updated_at > SEEDED_UPDATED_AT
        for match_id, before in untouched_before.items():
            assert _match_row(test_database, match_id) == before

        command.downgrade(config, PREVIOUS_REVISION)
        for match_id, expected in (
            (WRONG_DAY_MATCH, dt.datetime(2026, 7, 11, 0, 0, 0)),
            (SAME_DAY_MATCH, dt.datetime(2026, 7, 12, 0, 0, 0)),
            (NO_MAP_MATCH, dt.datetime(2026, 7, 13, 0, 0, 0)),
            (EXACT_MATCH, dt.datetime(2026, 7, 14, 0, 0, 0)),
            (FALLBACK_ONLY_MATCH, dt.datetime(2026, 7, 15, 0, 0, 0)),
        ):
            date, _, _ = _match_row(test_database, match_id)
            assert date == expected
    finally:
        _cleanup(test_database)
        command.upgrade(config, "head")
