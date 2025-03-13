"""Scraping module for fetching match, player, and demo data."""
try:
    from .match_scraper import MatchScraper
    from .demo_scraper import DemoScraper
    from .results_scraper import ResultsScraper
    __all__ = ["MatchScraper", "DemoScraper"]
except ImportError as e:
    print(f"❌ Error importing scraping module: {e}")
    MatchScraper = None
    DemoScraper = None
