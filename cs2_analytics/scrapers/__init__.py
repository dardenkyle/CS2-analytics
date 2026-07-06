"""Scraping module for fetching match, player, and demo data."""

from .map_scraper import MapScraper
from .match_scraper import MatchScraper
from .results_scraper import ResultsScraper

__all__ = ["ResultsScraper", "MatchScraper", "MapScraper"]
