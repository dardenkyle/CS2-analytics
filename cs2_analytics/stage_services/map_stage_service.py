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
    """Coordinates one map ingestion item.

    Branch 1 defines the dependency boundary only. Controller wiring and
    workflow migration happen in later Phase 3 branches.
    """

    def __init__(
        self,
        scraper: MapScraper,
        parser: MapParser,
        store_players: Callable[[list[Player]], None],
        map_state: MapIngestionState,
    ) -> None:
        self.scraper = scraper
        self.parser = parser
        self.store_players = store_players
        self.map_state = map_state

    def process_item(self, map_id: str, map_url: str) -> None:
        """Process one map ingestion-state row."""
        raise NotImplementedError
