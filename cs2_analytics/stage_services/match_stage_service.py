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
    """Coordinates one match ingestion item."""

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

    def process_item(self, match_id: str, match_url: str) -> bool:
        """Process one match ingestion-state row.

        Returns True when the match was stored successfully and False when
        parsing returned no match object.
        """
        self.match_state.mark_as_processing(match_id)
        soup = self.scraper.fetch_soup(match_url)
        match, map_links, demo_links = self.parser.parse_match(soup, match_url)

        if not match:
            self.match_state.mark_as_failed(match_id, "Parsing returned None")
            return False

        self.store_matches([match])
        self._queue_followups(map_links, demo_links)
        self.match_state.mark_as_processed(match_id)
        return True

    def _queue_followups(
        self,
        map_links: list[tuple[str, str]],
        demo_links: list[tuple[str, str]],
    ) -> None:
        """Queue map and demo links returned by the parser."""
        for map_id, map_url in map_links:
            self.map_state.queue(map_id, map_url, source="match_parser")
        for demo_id, demo_url in demo_links:
            self.demo_state.queue(demo_id, demo_url, source="match_parser")
