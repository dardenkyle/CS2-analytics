"""Match ingestion state manager."""

import datetime as dt

from cs2_analytics.exceptions import MatchIngestionStateError
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState


class MatchIngestionState(BaseIngestionState[int]):
    """Ingestion-state manager for match discovery and processing."""

    def __init__(self) -> None:
        super().__init__(
            table_name="match_ingestion_state",
            id_field="match_id",
            url_field="match_url",
            error_cls=MatchIngestionStateError,
        )

    def mark_as_partial(self, id_value: int) -> None:
        """Marks the match as processed with maps still in non-terminal states.

        Reserved for the match-complete processing unit: a match is partial
        when it was processed but not all of its maps reached a terminal
        state.
        """
        now = dt.datetime.now()
        query = """
        UPDATE match_ingestion_state
        SET status = 'partial', last_updated_at = %s
        WHERE match_id = %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (now, id_value))
        except Exception as e:
            raise self.error_cls(
                "Failed to mark item as partial in match_ingestion_state."
            ) from e
