"""Per-item demo stage workflow service."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from cs2_analytics.stage_services.stage_result import StageItemResult

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
        store_demo_file: Callable[[int, str, str | None, bool, bool, bool], None],
        demo_state: DemoIngestionState,
    ) -> None:
        self.scraper = scraper
        self.parser = parser
        self.store_demo_file = store_demo_file
        self.demo_state = demo_state

    def process_item(self, demo_id: str, demo_url: str) -> StageItemResult:
        """Process one demo ingestion-state row.

        Demo ingestion is intentionally deferred. Returning an explicit skipped
        result keeps controller summaries honest without expanding the
        non-operational demo pipeline in this branch.
        """
        _ = demo_url
        message = "Demo ingestion is deferred until the demo pipeline is operational"
        self.demo_state.mark_as_skipped(
            demo_id,
            message,
        )
        return StageItemResult.skipped(message)
