"""Round-trip test for migration 20261027_0007.

Runs against the local test database. Seeds matches at midnight the way
the old match parser wrote them, with maps carrying the UTC instants the
map parser has always written, runs the upgrade, and checks that a match
whose day disagreed with its first map moves to that map's instant, a
match on the right day gains the time of day, a match with no maps is
left alone, and a match already equal to its first map is not rewritten
at all. Then downgrades to confirm the midnight rendering and upgrades
again so the shared database is left at head.
"""

import datetime as dt
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREVIOUS_REVISION = "20260923_0006"

WRONG_DAY_MATCH, SAME_DAY_MATCH, NO_MAP_MATCH, EXACT_MATCH = 9101, 9102, 9103, 9104
MAP_IDS = (8101, 8102, 8103, 8104)


def _naive(*parts: int) -> dt.datetime:
    return dt.datetime(*parts)


def _alembic_config() -> Config:
    backend_root = PROJECT_ROOT / "cs2_analytics"
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("prepend_sys_path", str(PROJECT_ROOT))
    return config


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
        ):
            cur.execute(
                """
                INSERT INTO matches (match_id, match_url, team1, team2, winner, date,
                                     last_scraped_at)
                VALUES (%s, %s, 'A', 'B', 'A', %s, '2026-07-20 12:00:00+00');
                """,
                (match_id, f"https://example.test/m/{match_id}", date),
            )
        for map_id, match_id, map_order, date in (
            (MAP_IDS[0], WRONG_DAY_MATCH, 1, "2026-07-11 02:00:00"),
            (MAP_IDS[1], WRONG_DAY_MATCH, 2, "2026-07-11 03:30:00"),
            (MAP_IDS[2], SAME_DAY_MATCH, 1, "2026-07-12 18:00:00"),
            (MAP_IDS[3], EXACT_MATCH, 1, "2026-07-14 15:00:00"),
        ):
            cur.execute(
                """
                INSERT INTO maps (map_id, match_id, map_url, map_order, map_name,
                                  team1_score, team2_score, map_winner, date,
                                  last_scraped_at)
                VALUES (%s, %s, %s, %s, 'de_test', 13, 7, 'A', %s,
                        '2026-07-20 12:00:00+00');
                """,
                (map_id, match_id, f"https://example.test/p/{map_id}", map_order, date),
            )


def _match_date(database, match_id: int) -> dt.datetime:
    with database.get_cursor() as cur:
        cur.execute("SELECT date FROM matches WHERE match_id = %s;", (match_id,))
        (value,) = cur.fetchone()
    return value


def _row_version(database, match_id: int) -> int:
    """The row's transaction id, which changes only when the row is rewritten."""
    with database.get_cursor() as cur:
        cur.execute(
            "SELECT xmin::text::bigint FROM matches WHERE match_id = %s;", (match_id,)
        )
        (value,) = cur.fetchone()
    return value


def _cleanup(database) -> None:
    with database.get_cursor() as cur:
        cur.execute("DELETE FROM maps WHERE map_id = ANY(%s);", (list(MAP_IDS),))
        cur.execute(
            "DELETE FROM matches WHERE match_id = ANY(%s);",
            ([WRONG_DAY_MATCH, SAME_DAY_MATCH, NO_MAP_MATCH, EXACT_MATCH],),
        )


@pytest.mark.usefixtures("test_database")
def test_upgrade_sets_match_date_from_first_map_and_leaves_the_rest(
    test_database,
) -> None:
    config = _alembic_config()
    try:
        command.downgrade(config, PREVIOUS_REVISION)
        _seed(test_database)
        exact_before = _row_version(test_database, EXACT_MATCH)
        no_map_before = _row_version(test_database, NO_MAP_MATCH)

        command.upgrade(config, "head")

        assert _match_date(test_database, WRONG_DAY_MATCH) == _naive(
            2026, 7, 11, 2, 0, 0
        )
        assert _match_date(test_database, SAME_DAY_MATCH) == _naive(
            2026, 7, 12, 18, 0, 0
        )
        assert _match_date(test_database, NO_MAP_MATCH) == _naive(2026, 7, 13, 0, 0, 0)
        assert _match_date(test_database, EXACT_MATCH) == _naive(2026, 7, 14, 15, 0, 0)
        assert _row_version(test_database, EXACT_MATCH) == exact_before
        assert _row_version(test_database, NO_MAP_MATCH) == no_map_before

        command.downgrade(config, PREVIOUS_REVISION)
        assert _match_date(test_database, WRONG_DAY_MATCH) == _naive(
            2026, 7, 11, 0, 0, 0
        )
        assert _match_date(test_database, SAME_DAY_MATCH) == _naive(
            2026, 7, 12, 0, 0, 0
        )
        assert _match_date(test_database, NO_MAP_MATCH) == _naive(2026, 7, 13, 0, 0, 0)
        assert _match_date(test_database, EXACT_MATCH) == _naive(2026, 7, 14, 0, 0, 0)
    finally:
        _cleanup(test_database)
        command.upgrade(config, "head")
