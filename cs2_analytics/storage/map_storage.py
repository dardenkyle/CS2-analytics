from cs2_analytics.exceptions import MapStorageError
from cs2_analytics.models.map import Map
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


def store_maps(maps: list[Map]) -> None:
    if not maps:
        return

    insert_query = """
    INSERT INTO maps (
        map_id, match_id, map_url, map_order, map_name,
        team1_score, team2_score, map_winner, date,
        inserted_at, last_scraped_at, last_updated_at, data_complete
    )
    VALUES (
        %(map_id)s, %(match_id)s, %(map_url)s, %(map_order)s, %(map_name)s,
        %(team1_score)s, %(team2_score)s, %(map_winner)s, %(date)s,
        %(inserted_at)s, %(last_scraped_at)s, %(last_updated_at)s, %(data_complete)s
    )
    ON CONFLICT (map_id) DO UPDATE SET
        match_id = EXCLUDED.match_id,
        map_url = EXCLUDED.map_url,
        map_order = EXCLUDED.map_order,
        map_name = EXCLUDED.map_name,
        team1_score = EXCLUDED.team1_score,
        team2_score = EXCLUDED.team2_score,
        map_winner = EXCLUDED.map_winner,
        date = EXCLUDED.date,
        last_scraped_at = EXCLUDED.last_scraped_at,
        last_updated_at = EXCLUDED.last_updated_at,
        data_complete = EXCLUDED.data_complete;
    """

    try:
        db = get_db()
        with db.get_cursor() as cur:
            for map_obj in maps:
                cur.execute(
                    insert_query,
                    {
                        "map_id": map_obj.map_id,
                        "match_id": map_obj.match_id,
                        "map_url": map_obj.map_url,
                        "map_order": map_obj.map_order,
                        "map_name": map_obj.map_name,
                        "team1_score": map_obj.team1_score,
                        "team2_score": map_obj.team2_score,
                        "map_winner": map_obj.map_winner,
                        "date": map_obj.date,
                        "inserted_at": map_obj.inserted_at,
                        "last_scraped_at": map_obj.last_scraped_at,
                        "last_updated_at": map_obj.last_updated_at,
                        "data_complete": map_obj.data_complete,
                    },
                )
            logger.info("Stored %d map records.", len(maps))
    except Exception as e:
        raise MapStorageError("Failed to store map records.") from e
