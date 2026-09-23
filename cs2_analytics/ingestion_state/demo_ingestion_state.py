"""Demo ingestion state manager."""

from cs2_analytics.exceptions import DemoIngestionStateError
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState


class DemoIngestionState(BaseIngestionState[str]):
    """Ingestion-state manager for demo discovery and processing."""

    def __init__(self) -> None:
        super().__init__(
            table_name="demo_ingestion_state",
            id_field="demo_id",
            url_field="demo_url",
            error_cls=DemoIngestionStateError,
        )

    def queue(
        self,
        id_value: str,
        url: str,
        source: str = "unknown",
        priority: int = 0,
        cur=None,
        *,
        match_id: int | None = None,
    ) -> None:
        """Add or refresh a demo ingestion row with its parent match.

        When cur is provided the statement joins the caller's transaction
        and the caller owns commit/rollback (ADR-0013); otherwise the write
        runs in its own transaction as before.
        """
        query = """
        INSERT INTO demo_ingestion_state (
            demo_id, demo_url, match_id, status, source, priority,
            first_seen_at, last_seen_at, last_updated_at
        )
        VALUES (%s, %s, %s, 'discovered', %s, %s, now(), now(), now())
        ON CONFLICT (demo_id) DO UPDATE
        SET demo_url = EXCLUDED.demo_url,
            match_id = COALESCE(EXCLUDED.match_id, demo_ingestion_state.match_id),
            source = EXCLUDED.source,
            priority = GREATEST(
                COALESCE(demo_ingestion_state.priority, 0),
                EXCLUDED.priority
            ),
            last_seen_at = EXCLUDED.last_seen_at,
            last_updated_at = EXCLUDED.last_updated_at;
        """
        params = (id_value, url, match_id, source, priority)
        try:
            if cur is not None:
                cur.execute(query, params)
            else:
                with self.db.get_cursor() as own_cur:
                    own_cur.execute(query, params)
        except Exception as e:
            raise self.error_cls(
                "Failed to record ingestion state item in demo_ingestion_state."
            ) from e
