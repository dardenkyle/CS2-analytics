"""Seed a small fixture dataset for the CI dbt build.

Writes two matches, four maps, and six player-map rows through the real
storage layer so the CI dbt job (ci.yml, dbt-build) has source data that
exercises the grain, relationship, and derivation tests meaningfully:
match winners equal one of the two team names (losing_team stays
non-null), map names repeat across matches (dim_maps grain), and one
player appears across maps and dates (current-team derivation and the
SCD2 snapshot).

Intended for disposable databases only. The script refuses to run when
DB_HOST is not local unless --allow-remote is passed explicitly.
"""

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta

from cs2_analytics.models.map import Map
from cs2_analytics.models.match import Match
from cs2_analytics.models.player import Player
from cs2_analytics.storage.map_storage import store_maps
from cs2_analytics.storage.match_storage import store_matches
from cs2_analytics.storage.player_storage import store_players
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

LOCAL_HOSTS = ("localhost", "127.0.0.1", "db")
FIXTURE_MATCH_IDS = (940_000_001, 940_000_002)
FIXTURE_MAP_IDS = (940_000_101, 940_000_102, 940_000_103, 940_000_104)
FIXTURE_PLAYER_IDS = (940_000_201, 940_000_202, 940_000_203)

TEAM_ALPHA = "Fixture Alpha"
TEAM_BRAVO = "Fixture Bravo"
TEAM_CHARLIE = "Fixture Charlie"


def require_local_database(allow_remote: bool) -> None:
    """Refuse to write anywhere but a local database without explicit opt-in."""
    db_host = os.getenv("DB_HOST", "")
    if allow_remote or db_host in LOCAL_HOSTS:
        return
    raise RuntimeError(
        f"DB_HOST={db_host!r} is not local; pass --allow-remote to seed a"
        " non-local disposable database on purpose."
    )


def fixture_matches(now: datetime) -> list[Match]:
    """Two matches sharing a team so roster derivation spans dates."""
    earlier = (now - timedelta(days=2)).isoformat()
    later = (now - timedelta(days=1)).isoformat()
    return [
        Match(
            match_id=FIXTURE_MATCH_IDS[0],
            match_url=f"https://fixture.local/matches/{FIXTURE_MATCH_IDS[0]}",
            map_links=[
                (map_id, f"https://fixture.local/stats/maps/{map_id}")
                for map_id in FIXTURE_MAP_IDS[:3]
            ],
            demo_links=[],
            team1=TEAM_ALPHA,
            team2=TEAM_BRAVO,
            score1=2,
            score2=1,
            winner=TEAM_ALPHA,
            event="CI Fixture Cup",
            match_type="bo3",
            forfeit=False,
            date=earlier,
            last_inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        ),
        Match(
            match_id=FIXTURE_MATCH_IDS[1],
            match_url=f"https://fixture.local/matches/{FIXTURE_MATCH_IDS[1]}",
            map_links=[
                (
                    FIXTURE_MAP_IDS[3],
                    f"https://fixture.local/stats/maps/{FIXTURE_MAP_IDS[3]}",
                )
            ],
            demo_links=[],
            team1=TEAM_ALPHA,
            team2=TEAM_CHARLIE,
            score1=0,
            score2=1,
            winner=TEAM_CHARLIE,
            event="CI Fixture Cup",
            match_type="bo1",
            forfeit=False,
            date=later,
            last_inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        ),
    ]


def fixture_maps(now: datetime) -> list[Map]:
    """Four maps; Mirage repeats across matches to exercise dim_maps grain."""
    earlier = (now - timedelta(days=2)).isoformat()
    later = (now - timedelta(days=1)).isoformat()
    specs = [
        (FIXTURE_MAP_IDS[0], FIXTURE_MATCH_IDS[0], "Mirage", 1, 13, 7, TEAM_ALPHA, earlier),
        (FIXTURE_MAP_IDS[1], FIXTURE_MATCH_IDS[0], "Inferno", 2, 9, 13, TEAM_BRAVO, earlier),
        (FIXTURE_MAP_IDS[2], FIXTURE_MATCH_IDS[0], "Nuke", 3, 13, 11, TEAM_ALPHA, earlier),
        (FIXTURE_MAP_IDS[3], FIXTURE_MATCH_IDS[1], "Mirage", 1, 8, 13, TEAM_CHARLIE, later),
    ]
    return [
        Map(
            map_id=map_id,
            match_id=match_id,
            map_url=f"https://fixture.local/stats/maps/{map_id}",
            map_name=map_name,
            map_order=map_order,
            team1_score=score1,
            team2_score=score2,
            map_winner=winner,
            date=date,
            inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )
        for map_id, match_id, map_name, map_order, score1, score2, winner, date in specs
    ]


def fixture_players(now: datetime) -> list[Player]:
    """Six player-map rows over three players and two teams per map."""
    specs = [
        (FIXTURE_MAP_IDS[0], FIXTURE_PLAYER_IDS[0], "fixA1", TEAM_ALPHA, "Mirage", 1.35),
        (FIXTURE_MAP_IDS[0], FIXTURE_PLAYER_IDS[1], "fixB1", TEAM_BRAVO, "Mirage", 0.87),
        (FIXTURE_MAP_IDS[1], FIXTURE_PLAYER_IDS[0], "fixA1", TEAM_ALPHA, "Inferno", 1.02),
        (FIXTURE_MAP_IDS[1], FIXTURE_PLAYER_IDS[1], "fixB1", TEAM_BRAVO, "Inferno", 1.18),
        (FIXTURE_MAP_IDS[3], FIXTURE_PLAYER_IDS[0], "fixA1", TEAM_ALPHA, "Mirage", 0.95),
        (FIXTURE_MAP_IDS[3], FIXTURE_PLAYER_IDS[2], "fixC1", TEAM_CHARLIE, "Mirage", 1.44),
    ]
    return [
        Player(
            map_id=map_id,
            player_id=player_id,
            player_name=player_name,
            player_url=f"https://fixture.local/player/{player_id}",
            map_name=map_name,
            team_name=team_name,
            kills=20,
            headshots=10,
            assists=4,
            flash_assists=2,
            deaths=15,
            traded_deaths=3,
            opening_kills=2,
            opening_deaths=1,
            multi_kills=3,
            clutches_won=1,
            kast=72.5,
            kd_diff=5,
            adr=81.3,
            fk_diff=1,
            round_swing=0.1,
            rating=rating,
            last_inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )
        for map_id, player_id, player_name, team_name, map_name, rating in specs
    ]


def main() -> int:
    """Seed the fixture rows through the storage layer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Permit seeding a non-local disposable database.",
    )
    args = parser.parse_args()

    require_local_database(args.allow_remote)
    now = datetime.now(UTC)
    store_matches(fixture_matches(now))
    store_maps(fixture_maps(now))
    store_players(fixture_players(now))
    logger.info(
        "Seeded dbt CI fixture: %d matches, %d maps, %d player rows.",
        len(FIXTURE_MATCH_IDS),
        len(FIXTURE_MAP_IDS),
        6,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
