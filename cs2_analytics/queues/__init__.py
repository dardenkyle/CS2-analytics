"""
Initializes scrape queue managers and ingestion-state compatibility exports.

This allows direct imports like:
    from cs2_analytics.queues import match_queue, map_queue, demo_queue
    from cs2_analytics.queues import MatchIngestionState
"""

from cs2_analytics.queues.demo_ingestion_state import DemoIngestionState
from cs2_analytics.queues.demo_scrape_queue import DemoScrapeQueue
from cs2_analytics.queues.map_ingestion_state import MapIngestionState
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
from cs2_analytics.queues.match_ingestion_state import MatchIngestionState
from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue

match_queue = MatchScrapeQueue()
map_queue = MapScrapeQueue()
demo_queue = DemoScrapeQueue()

__all__ = [
    "DemoIngestionState",
    "DemoScrapeQueue",
    "MapIngestionState",
    "MapScrapeQueue",
    "MatchIngestionState",
    "MatchScrapeQueue",
    "demo_queue",
    "map_queue",
    "match_queue",
]
