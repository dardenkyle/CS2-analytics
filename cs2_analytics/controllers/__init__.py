"""
The `controllers` package contains orchestration logic that coordinates
scraping, parsing, and storage for each stage of the CS2 data pipeline.

Each controller:
- Pulls items from its respective scrape queue
- Uses a scraper to fetch HTML or raw content
- Uses a parser to extract structured data
- Stores the results and updates queue status

Controllers enable modular batch processing for automation or scheduled runs.
"""

from .match_controller import MatchController
from .map_controller import MapController
from .demo_controller import DemoController

__all__ = [
    "MatchController",
    "MapController",
    "DemoController",
]
