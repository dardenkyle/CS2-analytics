"""
The `storage` package provides a centralized interface for all database-related
interactions including:

- Database connections and session management
- Scrape queue managers for matches, maps, and demos
- Data models representing persistent entities
"""

from storage.base_scrape_queue import BaseScrapeQueue
from storage.demo_scrape_queue import DemoScrapeQueue
from storage.map_scrape_queue import MapScrapeQueue
from storage.match_scrape_queue import MatchScrapeQueue
from storage.storage_models import Match, Player
from storage.db_instance import db

# Instantiate queue managers for convenience
try:
    demo_queue: DemoScrapeQueue = DemoScrapeQueue()
    match_queue: MatchScrapeQueue = MatchScrapeQueue()
    map_queue: MapScrapeQueue = MapScrapeQueue()
except Exception as e:
    raise RuntimeError(f"Failed to initialize queue managers: {e}")

__all__ = [
    "db",
    "demo_queue",
    "match_queue",
    "map_queue",
    "DemoScrapeQueue",
    "MatchScrapeQueue",
    "MapScrapeQueue",
    "BaseScrapeQueue",
    "Database",
    "Match",
    "Player",
]
