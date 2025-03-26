"""Scraping module for fetching match, player, and demo data."""

from .results_scraper import ResultsScraper
from .match_scraper import MatchScraper
from .map_scraper import MapScraper
from .demo_scraper import DemoScraper

__all__ = ["ResultsScraper", "MatchScraper", "MapScraper", "DemoScraper"]
