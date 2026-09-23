"""Round-trip test for migrations 20260923_0005 and 20260923_0006.

Runs against the local test database. Seeds naive ingestion-state rows
the way both historical writers produced them (a UTC container and the
Central desktop), runs the upgrade, and checks that demo rows gained
their parent match from `matches.demo_links` and that every timestamp
became the correct UTC instant: witnessed values by the UTC clock,
everything else by America/Chicago, across both daylight and standard
time. Then downgrades to confirm the naive Central rendering and
upgrades again so the shared database is left at head.
"""

import datetime as dt
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREVIOUS_REVISION = "20260901_0004"

STATE_COLUMNS = (
    "first_seen_at",
    "last_seen_at",
    "last_attempted_at",
    "last_processed_at",
    "last_failed_at",
    "last_updated_at",
)
STATE_TABLES = ("match_ingestion_state", "map_ingestion_state", "demo_ingestion_state")

UTC_MATCH, CDT_MATCH, CST_MATCH, PENDING_MATCH = 9001, 9002, 9003, 9004
UTC_MAP, CDT_MAP, UTC_PROCESSED_MAP, COLLISION_MAP = 8001, 8002, 8003, 8004
# Demo ids are numeric strings, as the source issues them and as the
# demo_links backfill regexp expects.
UTC_DEMO, CDT_DEMO = "909001", "909002"


def _utc(*parts: int) -> dt.datetime:
    return dt.datetime(*parts, tzinfo=dt.UTC)


def _alembic_config() -> Config:
    backend_root = PROJECT_ROOT / "cs2_analytics"
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("prepend_sys_path", str(PROJECT_ROOT))
    return config


def _seed(database) -> None:
    """Insert naive rows exactly as the two historical writers stored them."""
    with database.get_cursor() as cur:
        for match_id, scraped, demo_id in (
            (UTC_MATCH, _utc(2026, 7, 10, 18, 0, 0), UTC_DEMO),
            (CDT_MATCH, _utc(2026, 7, 10, 18, 0, 0), CDT_DEMO),
            (CST_MATCH, _utc(2026, 1, 10, 18, 0, 0), None),
        ):
            # demo_links holds the parser's pairs verbatim, which is how the
            # 20260923_0005 backfill finds each demo's parent.
            demo_links = (
                f"[('{demo_id}', 'https://example.test/d/{demo_id}')]"
                if demo_id is not None
                else "[]"
            )
            cur.execute(
                """
                INSERT INTO matches (match_id, match_url, team1, team2, winner, date,
                                     last_scraped_at, demo_links)
                VALUES (%s, %s, 'A', 'B', 'A', '2026-01-01', %s, %s);
                """,
                (match_id, f"https://example.test/m/{match_id}", scraped, demo_links),
            )
        # A map the source row witnesses as processed by a UTC clock, so the
        # map-stage processing witness is exercised even though production
        # has no such rows today; and the #219 collision map, discovered by
        # the UTC parent at 18:00:03Z and processed from Central at 23:05Z,
        # which the desktop stored as 18:05:00, within an hour of the
        # discovery stamp.
        for map_id, match_id, scraped in (
            (UTC_PROCESSED_MAP, CDT_MATCH, _utc(2026, 7, 15, 20, 0, 0)),
            (COLLISION_MAP, UTC_MATCH, _utc(2026, 7, 10, 23, 5, 0)),
        ):
            cur.execute(
                """
                INSERT INTO maps (map_id, match_id, map_url, map_order, map_name,
                                  team1_score, team2_score, map_winner, date,
                                  last_scraped_at)
                VALUES (%s, %s, %s, 2, 'de_test', 13, 7, 'A', '2026-01-01', %s);
                """,
                (map_id, match_id, f"https://example.test/p/{map_id}", scraped),
            )
        # A UTC container processed this match at 18:00:05Z, refreshed by
        # Central discovery sweeps later (last_seen_at).
        cur.execute(
            """
            INSERT INTO match_ingestion_state (match_id, match_url, status,
                first_seen_at, last_seen_at, last_attempted_at,
                last_processed_at, last_updated_at)
            VALUES (%s, %s, 'processed', '2026-07-10 17:30:00',
                    '2026-08-01 09:00:00', '2026-07-10 17:59:50',
                    '2026-07-10 18:00:05', '2026-07-10 18:00:05');
            """,
            (UTC_MATCH, f"https://example.test/m/{UTC_MATCH}"),
        )
        # The desktop processed this one at the same real instant, in CDT.
        cur.execute(
            """
            INSERT INTO match_ingestion_state (match_id, match_url, status,
                first_seen_at, last_seen_at, last_attempted_at,
                last_processed_at, last_updated_at)
            VALUES (%s, %s, 'processed', '2026-07-10 12:30:00',
                    '2026-07-10 13:00:05', '2026-07-10 12:59:50',
                    '2026-07-10 13:00:05', '2026-07-10 13:00:05');
            """,
            (CDT_MATCH, f"https://example.test/m/{CDT_MATCH}"),
        )
        # Same again in January, so the CST offset is exercised.
        cur.execute(
            """
            INSERT INTO match_ingestion_state (match_id, match_url, status,
                first_seen_at, last_seen_at, last_attempted_at,
                last_processed_at, last_updated_at)
            VALUES (%s, %s, 'processed', '2026-01-10 11:30:00',
                    '2026-01-10 12:00:00', '2026-01-10 11:59:50',
                    '2026-01-10 12:00:00', '2026-01-10 12:00:00');
            """,
            (CST_MATCH, f"https://example.test/m/{CST_MATCH}"),
        )
        # Never processed, so no witness: falls to Central.
        cur.execute(
            """
            INSERT INTO match_ingestion_state (match_id, match_url, status,
                first_seen_at, last_seen_at, last_failed_at, last_updated_at,
                failure_count)
            VALUES (%s, %s, 'failed', '2026-09-01 08:00:00', '2026-09-01 08:00:00',
                    '2026-09-01 08:05:00', '2026-09-01 08:05:00', 1);
            """,
            (PENDING_MATCH, f"https://example.test/m/{PENDING_MATCH}"),
        )
        # Children discovered inside each parent's processing transaction;
        # the UTC child was processed later from Central.
        cur.execute(
            """
            INSERT INTO map_ingestion_state (map_id, map_url, match_id, status,
                first_seen_at, last_seen_at, last_attempted_at,
                last_processed_at, last_updated_at)
            VALUES (%s, %s, %s, 'processed', '2026-07-10 18:00:03',
                    '2026-07-10 18:00:03', '2026-07-20 09:59:55',
                    '2026-07-20 10:00:00', '2026-07-20 10:00:00');
            """,
            (UTC_MAP, f"https://example.test/p/{UTC_MAP}", UTC_MATCH),
        )
        cur.execute(
            """
            INSERT INTO map_ingestion_state (map_id, map_url, match_id, status,
                first_seen_at, last_seen_at, last_updated_at)
            VALUES (%s, %s, %s, 'discovered', '2026-07-10 13:00:03',
                    '2026-07-10 13:00:03', '2026-07-10 13:00:03');
            """,
            (CDT_MAP, f"https://example.test/p/{CDT_MAP}", CDT_MATCH),
        )
        cur.execute(
            """
            INSERT INTO map_ingestion_state (map_id, map_url, match_id, status,
                first_seen_at, last_seen_at, last_attempted_at,
                last_processed_at, last_updated_at)
            VALUES (%s, %s, %s, 'processed', '2026-07-10 18:00:03',
                    '2026-07-10 18:00:03', '2026-07-10 18:04:55',
                    '2026-07-10 18:05:00', '2026-07-10 18:05:00');
            """,
            (COLLISION_MAP, f"https://example.test/p/{COLLISION_MAP}", UTC_MATCH),
        )
        # Discovered from Central with its parent, processed later by a UTC
        # container at 20:00:02Z.
        cur.execute(
            """
            INSERT INTO map_ingestion_state (map_id, map_url, match_id, status,
                first_seen_at, last_seen_at, last_attempted_at,
                last_processed_at, last_updated_at)
            VALUES (%s, %s, %s, 'processed', '2026-07-10 13:00:03',
                    '2026-07-10 13:00:03', '2026-07-15 19:59:55',
                    '2026-07-15 20:00:02', '2026-07-15 20:00:02');
            """,
            (UTC_PROCESSED_MAP, f"https://example.test/p/{UTC_PROCESSED_MAP}", CDT_MATCH),
        )
        for demo_id, seen in ((UTC_DEMO, "2026-07-10 18:00:04"), (CDT_DEMO, "2026-07-10 13:00:04")):
            cur.execute(
                """
                INSERT INTO demo_ingestion_state (demo_id, demo_url, status,
                    first_seen_at, last_seen_at, last_updated_at)
                VALUES (%s, %s, 'discovered', %s, %s, %s);
                """,
                (demo_id, f"https://example.test/d/{demo_id}", seen, seen, seen),
            )


def _row(database, table: str, id_column: str, item_id) -> dict[str, dt.datetime | None]:
    with database.get_cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(STATE_COLUMNS)} FROM {table} WHERE {id_column} = %s;",
            (item_id,),
        )
        values = cur.fetchone()
    return dict(zip(STATE_COLUMNS, values, strict=True))


def _demo_parent(database, demo_id: str) -> int | None:
    with database.get_cursor() as cur:
        cur.execute(
            "SELECT match_id FROM demo_ingestion_state WHERE demo_id = %s;", (demo_id,)
        )
        (match_id,) = cur.fetchone()
    return match_id


def _column_types(database) -> set[tuple[str, str, str]]:
    with database.get_cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_name = ANY(%s) AND column_name LIKE '%%_at'
               OR table_name = ANY(%s) AND column_name LIKE 'utc_%%';
            """,
            (list(STATE_TABLES), list(STATE_TABLES)),
        )
        return set(cur.fetchall())


def _cleanup(database) -> None:
    with database.get_cursor() as cur:
        cur.execute(
            "DELETE FROM map_ingestion_state WHERE map_id = ANY(%s);",
            ([UTC_MAP, CDT_MAP, UTC_PROCESSED_MAP, COLLISION_MAP],),
        )
        cur.execute(
            "DELETE FROM maps WHERE map_id = ANY(%s);",
            ([UTC_PROCESSED_MAP, COLLISION_MAP],),
        )
        cur.execute(
            "DELETE FROM demo_ingestion_state WHERE demo_id = ANY(%s);",
            ([UTC_DEMO, CDT_DEMO],),
        )
        cur.execute(
            "DELETE FROM match_ingestion_state WHERE match_id = ANY(%s);",
            ([UTC_MATCH, CDT_MATCH, CST_MATCH, PENDING_MATCH],),
        )
        cur.execute(
            "DELETE FROM matches WHERE match_id = ANY(%s);",
            ([UTC_MATCH, CDT_MATCH, CST_MATCH],),
        )


@pytest.mark.usefixtures("test_database")
def test_upgrade_converts_each_value_by_its_writers_clock(test_database) -> None:
    config = _alembic_config()
    try:
        command.downgrade(config, PREVIOUS_REVISION)
        _seed(test_database)
        command.upgrade(config, "head")

        types = _column_types(test_database)
        assert all(data_type == "timestamp with time zone" for _, _, data_type in types)
        assert {name for _, name, _ in types} == set(STATE_COLUMNS)

        # 20260923_0005: demo rows now carry the parent recorded in demo_links.
        assert _demo_parent(test_database, UTC_DEMO) == UTC_MATCH
        assert _demo_parent(test_database, CDT_DEMO) == CDT_MATCH

        utc_match = _row(test_database, "match_ingestion_state", "match_id", UTC_MATCH)
        assert utc_match["last_processed_at"] == _utc(2026, 7, 10, 18, 0, 5)
        assert utc_match["last_attempted_at"] == _utc(2026, 7, 10, 17, 59, 50)
        assert utc_match["first_seen_at"] == _utc(2026, 7, 10, 17, 30, 0)
        assert utc_match["last_updated_at"] == _utc(2026, 7, 10, 18, 0, 5)
        # Refreshed a month later from Central: not near the anchor.
        assert utc_match["last_seen_at"] == _utc(2026, 8, 1, 14, 0, 0)

        cdt_match = _row(test_database, "match_ingestion_state", "match_id", CDT_MATCH)
        assert cdt_match["last_processed_at"] == _utc(2026, 7, 10, 18, 0, 5)
        assert cdt_match["first_seen_at"] == _utc(2026, 7, 10, 17, 30, 0)

        cst_match = _row(test_database, "match_ingestion_state", "match_id", CST_MATCH)
        assert cst_match["last_processed_at"] == _utc(2026, 1, 10, 18, 0, 0)
        assert cst_match["first_seen_at"] == _utc(2026, 1, 10, 17, 30, 0)

        pending = _row(test_database, "match_ingestion_state", "match_id", PENDING_MATCH)
        assert pending["first_seen_at"] == _utc(2026, 9, 1, 13, 0, 0)
        assert pending["last_failed_at"] == _utc(2026, 9, 1, 13, 5, 0)
        assert pending["last_processed_at"] is None

        utc_map = _row(test_database, "map_ingestion_state", "map_id", UTC_MAP)
        assert utc_map["first_seen_at"] == _utc(2026, 7, 10, 18, 0, 3)
        assert utc_map["last_seen_at"] == _utc(2026, 7, 10, 18, 0, 3)
        assert utc_map["last_processed_at"] == _utc(2026, 7, 20, 15, 0, 0)
        assert utc_map["last_attempted_at"] == _utc(2026, 7, 20, 14, 59, 55)

        cdt_map = _row(test_database, "map_ingestion_state", "map_id", CDT_MAP)
        assert cdt_map["first_seen_at"] == _utc(2026, 7, 10, 18, 0, 3)

        # Map processing witnessed by maps.last_scraped_at: UTC for the
        # processing columns, Central for the earlier discovery columns.
        utc_map_run = _row(
            test_database, "map_ingestion_state", "map_id", UTC_PROCESSED_MAP
        )
        assert utc_map_run["last_processed_at"] == _utc(2026, 7, 15, 20, 0, 2)
        assert utc_map_run["last_attempted_at"] == _utc(2026, 7, 15, 19, 59, 55)
        assert utc_map_run["last_updated_at"] == _utc(2026, 7, 15, 20, 0, 2)
        assert utc_map_run["first_seen_at"] == _utc(2026, 7, 10, 18, 0, 3)

        # #219: discovery stamps keep the parent's UTC clock, processing
        # stamps keep the desktop's Central clock, although the naive
        # values sit five minutes apart.
        collision = _row(test_database, "map_ingestion_state", "map_id", COLLISION_MAP)
        assert collision["first_seen_at"] == _utc(2026, 7, 10, 18, 0, 3)
        assert collision["last_seen_at"] == _utc(2026, 7, 10, 18, 0, 3)
        assert collision["last_processed_at"] == _utc(2026, 7, 10, 23, 5, 0)
        assert collision["last_attempted_at"] == _utc(2026, 7, 10, 23, 4, 55)
        assert collision["last_updated_at"] == _utc(2026, 7, 10, 23, 5, 0)

        utc_demo = _row(test_database, "demo_ingestion_state", "demo_id", UTC_DEMO)
        cdt_demo = _row(test_database, "demo_ingestion_state", "demo_id", CDT_DEMO)
        assert utc_demo["first_seen_at"] == _utc(2026, 7, 10, 18, 0, 4)
        assert cdt_demo["first_seen_at"] == _utc(2026, 7, 10, 18, 0, 4)

        command.downgrade(config, PREVIOUS_REVISION)
        types = _column_types(test_database)
        assert all(data_type == "timestamp without time zone" for _, _, data_type in types)
        naive = _row(test_database, "match_ingestion_state", "match_id", UTC_MATCH)
        assert naive["last_processed_at"] == dt.datetime(2026, 7, 10, 13, 0, 5)
        naive = _row(test_database, "match_ingestion_state", "match_id", CST_MATCH)
        assert naive["last_processed_at"] == dt.datetime(2026, 1, 10, 12, 0, 0)
    finally:
        command.upgrade(config, "head")
        _cleanup(test_database)
