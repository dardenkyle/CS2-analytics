"""
The `controllers` package contains orchestration logic that coordinates
scraping, parsing, and storage for each stage of the CS2 data pipeline.

Each controller:
- Pulls ready items from its respective ingestion-state table
- Uses a scraper to fetch HTML or raw content
- Uses a parser to extract structured data
- Stores the results and updates ingestion lifecycle state

Controllers enable modular batch processing for automation or scheduled runs.
"""

from .map_controller import MapController
from .match_controller import MatchController
from .results_controller import ResultsController

__all__ = [
    "MatchController",
    "MapController",
    "ResultsController",
]
