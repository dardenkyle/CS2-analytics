from cs2_analytics.models.map import Map  # assumes your map model is called Map
from cs2_analytics.storage.db_instance import db
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


def store_maps(maps: list[Map]) -> None:
    if not maps:
        return

    insert_query = """
    INSERT INTO maps (
        map_id, match_id, map_name,
        team1_score, team2_score,
        last_inserted_at, last_scraped_at, last_updated_at, data_complete
    )
    VALUES (
        %(map_id)s, %(match_id)s, %(map_name)s,
        %(team1_score)s, %(team2_score)s,
        %(last_inserted_at)s, %(last_scraped_at)s, %(last_updated_at)s, %(data_complete)s
    )
    ON CONFLICT (map_id) DO UPDATE SET
        last_updated_at = EXCLUDED.last_updated_at;
    """

    with db.get_cursor() as cur:
        for map_obj in maps:
            cur.execute(insert_query, {
                "map_id": map_obj.map_id,
                "match_id": map_obj.match_id,
                "map_name": map_obj.map_name,
                "team1_score": map_obj.team1_score,
                "team2_score": map_obj.team2_score,
                "last_inserted_at": map_obj.last_inserted_at,
                "last_scraped_at": map_obj.last_scraped_at,
                "last_updated_at": map_obj.last_updated_at,
                "data_complete": map_obj.data_complete,
            })
        db.commit()
        logger.info("📥 Stored %d map records.", len(maps))
