"""
Initializes scrape queue managers for matches, maps, and demos.

This allows direct imports like:
    from cs2_analytics.queues import match_queue, map_queue, demo_queue
"""

from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
from cs2_analytics.queues.demo_scrape_queue import DemoScrapeQueue

match_queue = MatchScrapeQueue()
map_queue = MapScrapeQueue()
demo_queue = DemoScrapeQueue()

__all__ = ["match_queue", "map_queue", "demo_queue"]
