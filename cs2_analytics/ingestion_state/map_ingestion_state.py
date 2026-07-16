"""Map ingestion state manager."""

import datetime as dt

from cs2_analytics.exceptions import MapIngestionStateError
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState


class MapIngestionState(BaseIngestionState[int]):
    """Ingestion-state manager for map discovery and processing."""

    def __init__(self) -> None:
        super().__init__(
            table_name="map_ingestion_state",
            id_field="map_id",
            url_field="map_url",
            error_cls=MapIngestionStateError,
        )

    def fetch_with_match_context(
        self, limit: int = 25
    ) -> list[tuple[int, str, int | None, int | None]]:
        """Fetch pending map rows with parent match and map-order context."""
        query = """
        SELECT map_id, map_url, match_id, map_order
        FROM map_ingestion_state
        WHERE status = 'pending'
        ORDER BY priority DESC, first_seen_at ASC
        LIMIT %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (limit,))
                rows: list[tuple[int, str, int | None, int | None]] = cur.fetchall()
                return rows
        except Exception as e:
            raise self.error_cls(
                "Failed to fetch pending map items with match context."
            ) from e

    def queue(
        self,
        id_value: int,
        url: str,
        source: str = "unknown",
        priority: int = 0,
        cur=None,
        *,
        match_id: int | None = None,
        map_order: int | None = None,
    ) -> None:
        """Add or refresh a map ingestion row with parent match context.

        When cur is provided the statement joins the caller's transaction
        and the caller owns commit/rollback (ADR-0013); otherwise the write
        runs in its own transaction as before.
        """
        now = dt.datetime.now()
        query = """
        INSERT INTO map_ingestion_state (
            map_id, map_url, match_id, map_order, status, source, priority,
            first_seen_at, last_seen_at, last_updated_at
        )
        VALUES (%s, %s, %s, %s, 'pending', %s, %s, %s, %s, %s)
        ON CONFLICT (map_id) DO UPDATE
        SET map_url = EXCLUDED.map_url,
            match_id = COALESCE(EXCLUDED.match_id, map_ingestion_state.match_id),
            map_order = COALESCE(EXCLUDED.map_order, map_ingestion_state.map_order),
            source = EXCLUDED.source,
            priority = GREATEST(
                COALESCE(map_ingestion_state.priority, 0),
                EXCLUDED.priority
            ),
            last_seen_at = EXCLUDED.last_seen_at,
            last_updated_at = EXCLUDED.last_updated_at;
        """
        params = (
            id_value,
            url,
            match_id,
            map_order,
            source,
            priority,
            now,
            now,
            now,
        )
        try:
            if cur is not None:
                cur.execute(query, params)
            else:
                with self.db.get_cursor() as own_cur:
                    own_cur.execute(query, params)
        except Exception as e:
            raise self.error_cls(
                "Failed to record ingestion state item in map_ingestion_state."
            ) from e
