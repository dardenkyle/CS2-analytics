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

    def record_discovered(
        self,
        items: list[tuple[int, str, dt.date | None]],
        source: str = "results_scraper",
        priority: int = 0,
    ) -> int:
        """Adds or refreshes discovered matches with their result dates.

        Match-specific variant of record_many (#121): stores the
        results-section match_date at discovery time. On conflict the
        date only fills in when previously null or newly known
        (COALESCE), so a re-sweep dates old rows and never nulls an
        existing date. Returns the number of newly inserted rows so the
        caller can detect an all-known page (incremental early stop).
        """
        if not items:
            return 0

        query = """
        INSERT INTO match_ingestion_state (
            match_id, match_url, match_date, status, source, priority,
            first_seen_at, last_seen_at, last_updated_at
        )
        VALUES (%s, %s, %s, 'discovered', %s, %s, %s, %s, %s)
        ON CONFLICT (match_id) DO UPDATE
        SET match_url = EXCLUDED.match_url,
            match_date = COALESCE(EXCLUDED.match_date,
                                  match_ingestion_state.match_date),
            source = EXCLUDED.source,
            priority = GREATEST(
                COALESCE(match_ingestion_state.priority, 0),
                EXCLUDED.priority
            ),
            last_seen_at = EXCLUDED.last_seen_at,
            last_updated_at = EXCLUDED.last_updated_at
        RETURNING (xmax = 0) AS inserted;
        """
        now = dt.datetime.now()
        new_rows = 0
        try:
            with self.db.get_cursor() as cur:
                for match_id, url, match_date in items:
                    cur.execute(
                        query,
                        (match_id, url, match_date, source, priority, now, now, now),
                    )
                    row = cur.fetchone()
                    if row is not None and row[0]:
                        new_rows += 1
        except Exception as e:
            raise self.error_cls(
                "Failed to record discovered matches in match_ingestion_state."
            ) from e
        return new_rows

    def fetch_min_match_date(self) -> dt.date | None:
        """Returns the oldest recorded match_date - the backfill frontier.

        Null when no row carries a date yet (nothing discovered since the
        column landed). Backfill walks strictly backward, so this is the
        boundary between swept and unswept territory (#121).
        """
        query = "SELECT MIN(match_date) FROM match_ingestion_state;"
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
        except Exception as e:
            raise self.error_cls(
                "Failed to fetch min match_date from match_ingestion_state."
            ) from e
        min_date: dt.date | None = row[0] if row is not None else None
        return min_date

    def mark_as_partial(self, id_value: int) -> None:
        """Marks the match as processed with maps still in non-terminal states.

        Reserved for the match-complete processing unit: a match is partial
        when it was processed but not all of its maps reached a terminal
        state.
        """
        now = dt.datetime.now()
        query = """
        UPDATE match_ingestion_state
        SET status = 'partial', last_processed_at = %s, last_updated_at = %s
        WHERE match_id = %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (now, now, id_value))
        except Exception as e:
            raise self.error_cls(
                "Failed to mark item as partial in match_ingestion_state."
            ) from e
