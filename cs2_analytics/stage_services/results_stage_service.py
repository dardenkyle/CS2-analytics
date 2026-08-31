"""Results discovery persistence service."""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cs2_analytics.ingestion_state import MatchIngestionState


class ResultsStageService:
    """Records discovered match links in match ingestion state.

    Owns the persistence side of results discovery so the results scraper
    stays fetch-only: the scraper yields discovered
    (match_id, match_url, match_date) batches, and this service writes
    them as pending ingestion-state rows with their result dates (#121).
    """

    def __init__(
        self,
        match_state: MatchIngestionState,
        *,
        source: str = "results_scraper",
    ) -> None:
        self.match_state = match_state
        self.source = source

    def record_batch(
        self, batch: Sequence[tuple[int, str, dt.date | None]]
    ) -> tuple[int, int]:
        """Record one batch of discovered matches.

        Returns (recorded, newly_discovered): recorded is the batch size,
        newly_discovered counts rows that did not exist before. The
        controller uses a zero newly_discovered count on a non-empty
        batch to detect an all-known page (incremental early stop, #121).
        """
        if not batch:
            return 0, 0
        new_rows = self.match_state.record_discovered(
            list(batch), source=self.source
        )
        return len(batch), new_rows
