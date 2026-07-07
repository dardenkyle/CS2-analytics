"""Per-item map stage workflow service."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from cs2_analytics.stage_services.stage_result import StageItemResult

if TYPE_CHECKING:
    from cs2_analytics.ingestion_state import MapIngestionState
    from cs2_analytics.parsers.map_parser import MapParser
    from cs2_analytics.scrapers.map_scraper import MapScraper
    from cs2_analytics.storage.database import Database


class MapStageService:
    """Coordinates one map ingestion item."""

    def __init__(
        self,
        parser: MapParser,
        store_maps: Callable[..., None],
        store_players: Callable[..., None],
        map_state: MapIngestionState,
        db: Database,
    ) -> None:
        self.parser = parser
        self.store_maps = store_maps
        self.store_players = store_players
        self.map_state = map_state
        self.db = db

    def process_item(
        self,
        map_id: int,
        map_url: str,
        *,
        scraper: MapScraper,
        match_id: int | None = None,
        map_order: int | None = None,
    ) -> StageItemResult:
        """Process one map ingestion-state row.

        The parent match id is carried for Phase 3.5 map persistence.

        Returns the explicit per-item outcome after the service updates
        ingestion state.
        """
        soup = scraper.fetch_soup(map_url)
        parsed_map = self.parser.parse_map_details(
            soup,
            map_url,
            map_id,
            match_id=match_id,
            map_order=map_order,
        )

        if not parsed_map.players:
            message = "Parsing returned no player records"
            self.map_state.mark_as_failed(map_id, message)
            return StageItemResult.failed(message)

        with self.db.transaction() as cur:
            self.store_maps([parsed_map.map], cur=cur)
            self.store_players(parsed_map.players, cur=cur)
            self.map_state.mark_as_processed(map_id, cur=cur)
        return StageItemResult.processed()
