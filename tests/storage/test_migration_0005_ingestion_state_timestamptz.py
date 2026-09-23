"""Round-trip test for migration 20260923_0005 against the local test database.

Seeds naive ingestion-state rows the way both historical writers produced
them (a UTC container and the Central desktop), runs the upgrade, and
checks that every value became the correct UTC instant: witnessed values
by the UTC clock, everything else by America/Chicago, across both
daylight and standard time. Then downgrades to confirm the naive Central
rendering and upgrades again so the shared database is left at head.
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
UTC_MAP, CDT_MAP = 8001, 8002
UTC_DEMO, CDT_DEMO = "demo-9001", "demo-9002"


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
        for match_id, scraped in (
            (UTC_MATCH, _utc(2026, 7, 10, 18, 0, 0)),
            (CDT_MATCH, _utc(2026, 7, 10, 18, 0, 0)),
            (CST_MATCH, _utc(2026, 1, 10, 18, 0, 0)),
        ):
            cur.execute(
                """
                INSERT INTO matches (match_id, match_url, team1, team2, winner, date,
                                     last_scraped_at)
                VALUES (%s, %s, 'A', 'B', 'A', '2026-01-01', %s);
                """,
                (match_id, f"https://example.test/m/{match_id}", scraped),
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
            "DELETE FROM map_ingestion_state WHERE map_id = ANY(%s);", ([UTC_MAP, CDT_MAP],)
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
