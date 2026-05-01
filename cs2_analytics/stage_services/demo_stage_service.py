"""Per-item demo stage workflow service."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cs2_analytics.ingestion_state import DemoIngestionState
    from cs2_analytics.parsers.demo_parser import DemoParser
    from cs2_analytics.scrapers.demo_scraper import DemoScraper


class DemoStageService:
    """Coordinates one demo ingestion item.

    Demo processing remains deferred; this shell keeps Phase 3 structure aligned
    without expanding the active demo pipeline scope.
    """

    def __init__(
        self,
        scraper: DemoScraper,
        parser: DemoParser,
        store_demo_file: Callable[..., None],
        demo_state: DemoIngestionState,
    ) -> None:
        self.scraper = scraper
        self.parser = parser
        self.store_demo_file = store_demo_file
        self.demo_state = demo_state

    def process_item(self, demo_id: str, demo_url: str) -> None:
        """Process one demo ingestion-state row."""
        raise NotImplementedError
