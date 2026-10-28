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
        """Adds or refreshes discovered matches with their listing dates.

        Match-specific variant of record_many (#121): stores the UTC day
        of each entry's listing instant as a placeholder match_date. On
        conflict an existing date is kept and only a null is filled
        (COALESCE), so a re-sweep dates legacy undated rows but never
        replaces the match's own start day once `record_match_date` has
        written it (#215, ADR-0020). Returns the number of newly inserted
        rows so the caller can detect an all-known page (incremental
        early stop).
        """
        if not items:
            return 0

        query = """
        INSERT INTO match_ingestion_state (
            match_id, match_url, match_date, status, source, priority,
            first_seen_at, last_seen_at, last_updated_at
        )
        VALUES (%s, %s, %s, 'discovered', %s, %s, now(), now(), now())
        ON CONFLICT (match_id) DO UPDATE
        SET match_url = EXCLUDED.match_url,
            match_date = COALESCE(match_ingestion_state.match_date,
                                  EXCLUDED.match_date),
            source = EXCLUDED.source,
            priority = GREATEST(
                COALESCE(match_ingestion_state.priority, 0),
                EXCLUDED.priority
            ),
            last_seen_at = EXCLUDED.last_seen_at,
            last_updated_at = EXCLUDED.last_updated_at
        RETURNING (xmax = 0) AS inserted;
        """
        new_rows = 0
        try:
            with self.db.get_cursor() as cur:
                for match_id, url, match_date in items:
                    cur.execute(query, (match_id, url, match_date, source, priority))
                    row = cur.fetchone()
                    if row is not None and row[0]:
                        new_rows += 1
        except Exception as e:
            raise self.error_cls(
                "Failed to record discovered matches in match_ingestion_state."
            ) from e
        return new_rows

    def record_match_date(self, match_id: int, match_date: dt.date, cur=None) -> None:
        """Sets the row's match_date to the match's own UTC start day.

        Called by the match stage once the match page is parsed, so the
        column settles on the day the match started (#215, ADR-0020);
        the listing day discovery recorded is only a placeholder until
        then. Joins the caller's transaction when cur is given (ADR-0013).
        """
        query = """
        UPDATE match_ingestion_state
        SET match_date = %s
        WHERE match_id = %s;
        """
        params = (match_date, match_id)
        try:
            if cur is not None:
                cur.execute(query, params)
            else:
                with self.db.get_cursor() as own_cur:
                    own_cur.execute(query, params)
        except Exception as e:
            raise self.error_cls(
                "Failed to record match_date in match_ingestion_state."
            ) from e

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

    def fetch_max_match_date(self) -> dt.date | None:
        """Returns the newest recorded match_date - the incremental cursor.

        Null when no row carries a date yet. Incremental discovery walks
        forward day by day from just before this date to today, so it is
        the boundary between swept and unswept territory at the new end
        of the recorded range (#231), as `fetch_min_match_date` is at the
        old end.
        """
        query = "SELECT MAX(match_date) FROM match_ingestion_state;"
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
        except Exception as e:
            raise self.error_cls(
                "Failed to fetch max match_date from match_ingestion_state."
            ) from e
        max_date: dt.date | None = row[0] if row is not None else None
        return max_date

    def mark_as_partial(self, id_value: int) -> None:
        """Marks the match as processed with maps still in non-terminal states.

        Reserved for the match-complete processing unit: a match is partial
        when it was processed but not all of its maps reached a terminal
        state.
        """
        query = """
        UPDATE match_ingestion_state
        SET status = 'partial', last_processed_at = now(), last_updated_at = now()
        WHERE match_id = %s;
        """
        try:
            with self.db.get_cursor() as cur:
                cur.execute(query, (id_value,))
        except Exception as e:
            raise self.error_cls(
                "Failed to mark item as partial in match_ingestion_state."
            ) from e
