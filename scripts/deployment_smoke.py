"""Deterministic deployment smoke checks for the containerized runtime."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

from cs2_analytics.models.map import Map
from cs2_analytics.models.match import Match
from cs2_analytics.models.player import Player
from cs2_analytics.storage.database import Database
from cs2_analytics.storage.map_storage import store_maps
from cs2_analytics.storage.match_storage import store_matches
from cs2_analytics.storage.player_storage import store_players
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

REQUIRED_TABLES = ("matches", "maps", "players")
SMOKE_MATCH_ID = 930_000_001
SMOKE_MAP_ID = 930_000_101
SMOKE_PLAYER_ID = 930_000_201
SMOKE_PLAYER_NAME = "Smoke Test Player"


def main() -> int:
    """Run deterministic deployment smoke checks."""
    smoke_data_touched = False
    try:
        api_base_url = os.getenv("SMOKE_API_BASE_URL", "http://127.0.0.1:8000").rstrip(
            "/"
        )
        timeout_seconds = read_timeout_seconds()
        verify_migrated_tables()
        cleanup_smoke_source_rows()
        smoke_data_touched = True
        seed_smoke_source_rows()
        verify_api_health(api_base_url, timeout_seconds)
        verify_top_players_read(api_base_url, timeout_seconds)
    except Exception as exc:
        logger.exception("Deployment smoke check failed: %s", exc)
        return 1
    finally:
        if smoke_data_touched:
            try:
                cleanup_smoke_source_rows()
            except Exception as exc:
                logger.warning("Failed to clean up deployment smoke data: %s", exc)

    logger.info("Deployment smoke check passed.")
    return 0


def read_timeout_seconds() -> int:
    """Read the smoke HTTP timeout from the environment."""
    raw_value = os.getenv("SMOKE_API_TIMEOUT_SECONDS", "10")
    try:
        timeout_seconds = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("SMOKE_API_TIMEOUT_SECONDS must be an integer.") from exc

    if timeout_seconds <= 0:
        raise RuntimeError("SMOKE_API_TIMEOUT_SECONDS must be greater than zero.")

    return timeout_seconds


def verify_migrated_tables() -> None:
    """Confirm the expected source tables exist after migrations."""
    db = Database()
    missing_tables = []

    with db.get_cursor() as cur:
        for table_name in REQUIRED_TABLES:
            cur.execute("SELECT to_regclass(%s);", (f"public.{table_name}",))
            if cur.fetchone()[0] is None:
                missing_tables.append(table_name)

    if missing_tables:
        raise RuntimeError(
            "Missing migrated tables: " + ", ".join(sorted(missing_tables))
        )


def cleanup_smoke_source_rows() -> None:
    """Remove fixed-ID smoke rows from source tables."""
    db = Database()
    with db.get_cursor() as cur:
        cur.execute(
            "DELETE FROM players WHERE map_id = %s AND player_id = %s;",
            (SMOKE_MAP_ID, SMOKE_PLAYER_ID),
        )
        cur.execute("DELETE FROM maps WHERE map_id = %s;", (SMOKE_MAP_ID,))
        cur.execute("DELETE FROM matches WHERE match_id = %s;", (SMOKE_MATCH_ID,))


def seed_smoke_source_rows() -> None:
    """Seed repeat-safe source rows used by the API readiness check."""
    now = datetime.now(UTC)
    match_date = now.isoformat()

    store_matches(
        [
            Match(
                match_id=SMOKE_MATCH_ID,
                match_url=f"https://smoke.local/matches/{SMOKE_MATCH_ID}",
                map_links=[
                    (SMOKE_MAP_ID, f"https://smoke.local/stats/maps/{SMOKE_MAP_ID}")
                ],
                demo_links=[],
                team1="Smoke Alpha",
                team2="Smoke Beta",
                score1=13,
                score2=7,
                winner="Smoke Alpha",
                event="Deployment Smoke",
                match_type="bo1",
                forfeit=False,
                date=match_date,
                last_inserted_at=now,
                last_scraped_at=now,
                last_updated_at=now,
                data_complete=True,
            )
        ]
    )

    store_maps(
        [
            Map(
                map_id=SMOKE_MAP_ID,
                match_id=SMOKE_MATCH_ID,
                map_url=f"https://smoke.local/stats/maps/{SMOKE_MAP_ID}",
                map_name="Smoke",
                map_order=1,
                team1_score=13,
                team2_score=7,
                map_winner="Smoke Alpha",
                date=match_date,
                inserted_at=now,
                last_scraped_at=now,
                last_updated_at=now,
                data_complete=True,
            )
        ]
    )

    store_players(
        [
            Player(
                map_id=SMOKE_MAP_ID,
                player_id=SMOKE_PLAYER_ID,
                player_name=SMOKE_PLAYER_NAME,
                player_url=f"https://smoke.local/player/{SMOKE_PLAYER_ID}",
                map_name="Smoke",
                team_name="Smoke Alpha",
                kills=30,
                headshots=20,
                assists=5,
                flash_assists=2,
                deaths=4,
                traded_deaths=1,
                opening_kills=6,
                opening_deaths=1,
                multi_kills=8,
                clutches_won=2,
                kast=95.0,
                kd_diff=26,
                adr=150.0,
                fk_diff=5,
                round_swing=0.5,
                rating=9.99,
                last_inserted_at=now,
                last_scraped_at=now,
                last_updated_at=now,
                data_complete=True,
            )
        ]
    )


def verify_api_health(api_base_url: str, timeout_seconds: int) -> None:
    """Check the stable shallow API health endpoint."""
    payload = request_json(f"{api_base_url}/health", timeout_seconds)
    expected_payload = {"status": "ok", "service": "cs2-analytics-api"}
    if payload != expected_payload:
        raise RuntimeError(f"Unexpected health payload: {payload!r}")


def verify_top_players_read(api_base_url: str, timeout_seconds: int) -> None:
    """Check that the API can read seeded source data from PostgreSQL."""
    payload = request_json(
        f"{api_base_url}/api/top_players?min_maps=1&limit=100",
        timeout_seconds,
    )
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected top players list, got: {payload!r}")

    smoke_rows = [
        row
        for row in payload
        if isinstance(row, dict) and row.get("player_name") == SMOKE_PLAYER_NAME
    ]
    if not smoke_rows:
        raise RuntimeError("Seeded smoke player was not returned by top players API.")


def request_json(url: str, timeout_seconds: int) -> object:
    """Fetch a JSON endpoint and return the decoded payload."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to request {url}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Endpoint did not return valid JSON: {url}") from exc


if __name__ == "__main__":
    sys.exit(main())
