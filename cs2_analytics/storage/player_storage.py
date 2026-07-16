from cs2_analytics.exceptions import PlayerStorageError
from cs2_analytics.models.player import Player
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

INSERT_PLAYERS_QUERY = """
    INSERT INTO players (
        map_id, player_id, player_name, player_url, map_name,
        team_name, kills, headshots, assists, flash_assists, deaths, traded_deaths,
        opening_kills, opening_deaths, multi_kills, clutches_won,
        kast, kd_diff, adr, fk_diff, round_swing, rating,
        last_inserted_at, last_scraped_at, last_updated_at, data_complete
    )
    VALUES (
        %(map_id)s, %(player_id)s, %(player_name)s, %(player_url)s, %(map_name)s,
        %(team_name)s, %(kills)s, %(headshots)s, %(assists)s, %(flash_assists)s, %(deaths)s, %(traded_deaths)s,
        %(opening_kills)s, %(opening_deaths)s, %(multi_kills)s, %(clutches_won)s,
        %(kast)s, %(kd_diff)s, %(adr)s, %(fk_diff)s, %(round_swing)s, %(rating)s,
        %(last_inserted_at)s, %(last_scraped_at)s, %(last_updated_at)s, %(data_complete)s
    )
    ON CONFLICT (map_id, player_id) DO UPDATE SET
        player_name = EXCLUDED.player_name,
        player_url = EXCLUDED.player_url,
        map_name = EXCLUDED.map_name,
        team_name = EXCLUDED.team_name,
        kills = EXCLUDED.kills,
        headshots = EXCLUDED.headshots,
        assists = EXCLUDED.assists,
        flash_assists = EXCLUDED.flash_assists,
        deaths = EXCLUDED.deaths,
        traded_deaths = EXCLUDED.traded_deaths,
        opening_kills = EXCLUDED.opening_kills,
        opening_deaths = EXCLUDED.opening_deaths,
        multi_kills = EXCLUDED.multi_kills,
        clutches_won = EXCLUDED.clutches_won,
        kast = EXCLUDED.kast,
        kd_diff = EXCLUDED.kd_diff,
        adr = EXCLUDED.adr,
        fk_diff = EXCLUDED.fk_diff,
        round_swing = EXCLUDED.round_swing,
        rating = EXCLUDED.rating,
        last_scraped_at = EXCLUDED.last_scraped_at,
        last_updated_at = EXCLUDED.last_updated_at,
        data_complete = EXCLUDED.data_complete;
    """


def store_players(players: list[Player], cur=None) -> None:
    """Upsert player rows.

    When cur is provided the statements join the caller's transaction and
    the caller owns commit/rollback (ADR-0013); otherwise the write runs in
    its own transaction as before.
    """
    if not players:
        return

    try:
        if cur is not None:
            _execute_store_players(cur, players)
        else:
            with get_db().get_cursor() as own_cur:
                _execute_store_players(own_cur, players)
    except Exception as e:
        raise PlayerStorageError("Failed to store player records.") from e


def _execute_store_players(cur, players: list[Player]) -> None:
    values = [
        {
            "map_id": p.map_id,
            "player_id": p.player_id,
            "player_name": p.player_name,
            "player_url": p.player_url,
            "map_name": p.map_name,
            "team_name": p.team_name,
            "kills": p.kills,
            "headshots": p.headshots,
            "assists": p.assists,
            "flash_assists": p.flash_assists,
            "deaths": p.deaths,
            "traded_deaths": p.traded_deaths,
            "opening_kills": p.opening_kills,
            "opening_deaths": p.opening_deaths,
            "multi_kills": p.multi_kills,
            "clutches_won": p.clutches_won,
            "kast": p.kast,
            "kd_diff": p.kd_diff,
            "adr": p.adr,
            "fk_diff": p.fk_diff,
            "round_swing": p.round_swing,
            "rating": p.rating,
            "last_inserted_at": p.last_inserted_at,
            "last_scraped_at": p.last_scraped_at,
            "last_updated_at": p.last_updated_at,
            "data_complete": p.data_complete,
        }
        for p in players
    ]
    cur.executemany(INSERT_PLAYERS_QUERY, values)
    logger.info("Stored %d player stat records.", len(players))
