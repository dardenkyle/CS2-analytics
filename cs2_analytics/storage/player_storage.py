from cs2_analytics.models.player import Player
from cs2_analytics.storage.db_instance import db
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


def store_players(players: list[Player]) -> None:
    if not players:
        return

    insert_query = """
    INSERT INTO players (
        map_id, player_id, player_name, player_url, map_name,
        team_name, kills, headshots, assists, flash_assists, deaths,
        kast, kd_diff, adr, fk_diff, rating,
        last_inserted_at, last_scraped_at, last_updated_at, data_complete
    )
    VALUES (
        %(map_id)s, %(player_id)s, %(player_name)s, %(player_url)s, %(map_name)s,
        %(team_name)s, %(kills)s, %(headshots)s, %(assists)s, %(flash_assists)s, %(deaths)s,
        %(kast)s, %(kd_diff)s, %(adr)s, %(fk_diff)s, %(rating)s,
        %(last_inserted_at)s, %(last_scraped_at)s, %(last_updated_at)s, %(data_complete)s
    )
    ON CONFLICT (player_id, map_id) DO UPDATE SET
        last_updated_at = EXCLUDED.last_updated_at;
    """

    with db.get_cursor() as cur:
        for p in players:
            cur.execute(insert_query, {
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
                "kast": p.kast,
                "kd_diff": p.kd_diff,
                "adr": p.adr,
                "fk_diff": p.fk_diff,
                "rating": p.rating,
                "last_inserted_at": p.last_inserted_at,
                "last_scraped_at": p.last_scraped_at,
                "last_updated_at": p.last_updated_at,
                "data_complete": p.data_complete,
            })
        logger.info("📥 Stored %d player stat records.", len(players))
