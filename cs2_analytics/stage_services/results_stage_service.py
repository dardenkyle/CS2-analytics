"""Results discovery persistence service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cs2_analytics.utils.ingestion_state_helpers import chunk_and_record

if TYPE_CHECKING:
    from cs2_analytics.ingestion_state import MatchIngestionState


class ResultsStageService:
    """Records discovered match links in match ingestion state.

    Owns the persistence side of results discovery so the results scraper
    stays fetch-only: the scraper yields discovered (match_id, match_url)
    batches, and this service writes them as pending ingestion-state rows.
    """

    def __init__(
        self,
        match_state: MatchIngestionState,
        *,
        source: str = "results_scraper",
        chunk_size: int = 1000,
    ) -> None:
        self.match_state = match_state
        self.source = source
        self.chunk_size = chunk_size

    def record_batch(self, batch: list[tuple[int, str]]) -> int:
        """Record one batch of discovered matches; returns the count recorded."""
        if not batch:
            return 0
        chunk_and_record(
            items=list(batch),
            state_obj=self.match_state,
            chunk_size=self.chunk_size,
            source=self.source,
        )
        return len(batch)
