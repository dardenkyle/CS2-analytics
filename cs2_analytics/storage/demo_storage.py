from cs2_analytics.storage.db_instance import db
from cs2_analytics.utils.log_manager import get_logger
import datetime as dt

logger = get_logger(__name__)


def store_demo_file(
    map_id: int,
    demo_url: str,
    local_path: str = None,
    parsed: bool = False,
    heatmap_done: bool = False,
    grenade_analysis_done: bool = False,
) -> None:
    """
    Inserts or updates a demo file entry in the demo_files table.

    Args:
        map_id (int): Foreign key to maps table.
        demo_url (str): Download URL for the demo file.
        local_path (str, optional): Local path where the demo is saved.
        parsed (bool): Whether the demo has been parsed.
        heatmap_done (bool): Whether heatmap generation is complete.
        grenade_analysis_done (bool): Whether nade analysis is complete.
    """
    query = """
    INSERT INTO demo_files (
        map_id, demo_url, local_path,
        parsed, heatmap_done, grenade_analysis_done,
        last_inserted_at, last_processed_at
    )
    VALUES (
        %(map_id)s, %(demo_url)s, %(local_path)s,
        %(parsed)s, %(heatmap_done)s, %(grenade_analysis_done)s,
        %(last_inserted_at)s, %(last_processed_at)s
    )
    ON CONFLICT (map_id) DO UPDATE SET
        local_path = EXCLUDED.local_path,
        parsed = EXCLUDED.parsed,
        heatmap_done = EXCLUDED.heatmap_done,
        grenade_analysis_done = EXCLUDED.grenade_analysis_done,
        last_processed_at = EXCLUDED.last_processed_at;
    """

    now = dt.datetime.utcnow()

    values = {
        "map_id": map_id,
        "demo_url": demo_url,
        "local_path": local_path,
        "parsed": parsed,
        "heatmap_done": heatmap_done,
        "grenade_analysis_done": grenade_analysis_done,
        "last_inserted_at": now,
        "last_processed_at": now,
    }

    try:
        with db.get_cursor() as cur:
            cur.execute(query, values)
            db.commit()
            logger.info("📥 Stored demo file for map_id: %s", map_id)
    except Exception as e:
        logger.error("❌ Failed to store demo file for map_id %s: %s", map_id, e)
