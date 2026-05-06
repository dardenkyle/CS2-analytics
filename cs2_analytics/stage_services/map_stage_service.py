"""Per-item map stage workflow service."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cs2_analytics.ingestion_state import MapIngestionState
    from cs2_analytics.models.player import Player
    from cs2_analytics.parsers.map_parser import MapParser
    from cs2_analytics.scrapers.map_scraper import MapScraper


class MapStageService:
    """Coordinates one map ingestion item."""

    def __init__(
        self,
        parser: MapParser,
        store_players: Callable[[list[Player]], None],
        map_state: MapIngestionState,
    ) -> None:
        self.parser = parser
        self.store_players = store_players
        self.map_state = map_state

    def process_item(self, map_id: str, map_url: str, *, scraper: MapScraper) -> bool:
        """Process one map ingestion-state row.

        Returns True when player stats were stored successfully and False when
        parsing returned no player records.
        """
        soup = scraper.fetch_soup(map_url)
        players = self.parser.parse_map(soup, map_url, map_id)

        if not players:
            self.map_state.mark_as_failed(map_id, "Parsing returned None")
            return False

        self.store_players(players)
        self.map_state.mark_as_processed(map_id)
        return True
