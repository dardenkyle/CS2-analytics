"""Map ingestion state manager."""

import datetime as dt

from cs2_analytics.exceptions import MapQueueError
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState
from cs2_analytics.storage.db_instance import db


class MapIngestionState(BaseIngestionState):
    """Ingestion-state manager for map discovery and processing."""

    def __init__(self) -> None:
        super().__init__(
            table_name="map_ingestion_state",
            id_field="map_id",
            url_field="map_url",
            error_cls=MapQueueError,
        )

    def fetch_with_match_context(
        self, limit: int = 25
    ) -> list[tuple[str, str, int | None]]:
        """Fetch pending map rows with parent match context when available."""
        query = """
        SELECT map_id, map_url, match_id
        FROM map_ingestion_state
        WHERE status = 'pending'
        ORDER BY priority DESC, first_seen_at ASC
        LIMIT %s;
        """
        try:
            with db.get_cursor() as cur:
                cur.execute(query, (limit,))
                return cur.fetchall()
        except Exception as e:
            raise self.error_cls(
                "Failed to fetch pending map items with match context."
            ) from e

    def queue(
        self,
        id_value: str,
        url: str,
        source: str = "unknown",
        priority: int = 0,
        match_id: int | None = None,
    ) -> None:
        """Add or refresh a map ingestion row with parent match context."""
        now = dt.datetime.now()
        query = """
        INSERT INTO map_ingestion_state (
            map_id, map_url, match_id, status, source, priority,
            first_seen_at, last_seen_at, last_updated_at
        )
        VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s, %s)
        ON CONFLICT (map_id) DO UPDATE
        SET map_url = EXCLUDED.map_url,
            match_id = COALESCE(EXCLUDED.match_id, map_ingestion_state.match_id),
            source = EXCLUDED.source,
            priority = GREATEST(
                COALESCE(map_ingestion_state.priority, 0),
                EXCLUDED.priority
            ),
            last_seen_at = EXCLUDED.last_seen_at,
            last_updated_at = EXCLUDED.last_updated_at;
        """
        try:
            with db.get_cursor() as cur:
                cur.execute(
                    query,
                    (id_value, url, match_id, source, priority, now, now, now),
                )
        except Exception as e:
            raise self.error_cls(
                "Failed to queue ingestion state item in map_ingestion_state."
            ) from e
