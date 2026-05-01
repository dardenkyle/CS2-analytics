"""Per-item match stage workflow service."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cs2_analytics.ingestion_state import (
        DemoIngestionState,
        MapIngestionState,
        MatchIngestionState,
    )
    from cs2_analytics.models.match import Match
    from cs2_analytics.parsers.match_parser import MatchParser
    from cs2_analytics.scrapers.match_scraper import MatchScraper


class MatchStageService:
    """Coordinates one match ingestion item.

    Branch 1 defines the dependency boundary only. Controller wiring and
    workflow migration happen in later Phase 3 branches.
    """

    def __init__(
        self,
        scraper: MatchScraper,
        parser: MatchParser,
        store_matches: Callable[[list[Match]], None],
        match_state: MatchIngestionState,
        map_state: MapIngestionState,
        demo_state: DemoIngestionState,
    ) -> None:
        self.scraper = scraper
        self.parser = parser
        self.store_matches = store_matches
        self.match_state = match_state
        self.map_state = map_state
        self.demo_state = demo_state

    def process_item(self, match_id: str, match_url: str) -> None:
        """Process one match ingestion-state row."""
        raise NotImplementedError
