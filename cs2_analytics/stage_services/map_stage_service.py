"""Per-item map stage workflow service."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from cs2_analytics.stage_services.stage_result import StageItemResult

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

    def process_item(
        self,
        map_id: int,
        map_url: str,
        *,
        scraper: MapScraper,
        match_id: int | None = None,  # noqa: ARG002
    ) -> StageItemResult:
        """Process one map ingestion-state row.

        The parent match id is carried for Phase 3.5 map persistence.

        Returns the explicit per-item outcome after the service updates
        ingestion state.
        """
        soup = scraper.fetch_soup(map_url)
        players = self.parser.parse_map(soup, map_url, map_id)

        if not players:
            message = "Parsing returned no player records"
            self.map_state.mark_as_failed(map_id, message)
            return StageItemResult.failed(message)

        self.store_players(players)
        self.map_state.mark_as_processed(map_id)
        return StageItemResult.processed()
