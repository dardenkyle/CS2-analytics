"""Tests results scraper functionality."""

from scrapers.results_scraper import ResultsScraper

scraper = ResultsScraper()

try:
    scraper.run(max_matches=10)
finally:
    scraper.close()
