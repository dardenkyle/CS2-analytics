"""Manually tests MapScraper by fetching queued map pages.

This helper bypasses controllers intentionally and is only for manual debugging.
"""

from cs2_analytics.ingestion_state import MapIngestionState
from cs2_analytics.scrapers.map_scraper import MapScraper

map_queue = MapIngestionState()


def main():
    """Main test function for MapScraper."""
    print("Starting MapScraper manual test...")

    queued_maps = map_queue.fetch(limit=3)
    if not queued_maps:
        print("No queued map links found. You may need to run MatchParser first.")
        return

    with MapScraper() as scraper:
        for map_id, map_url in queued_maps:
            soup = scraper.fetch_soup(map_url)
            print(f"Scraped map {map_id} from {map_url}. Soup length: {len(soup.text)}")

    print(f"Finished scraping {len(queued_maps)} map(s).")


if __name__ == "__main__":
    main()
