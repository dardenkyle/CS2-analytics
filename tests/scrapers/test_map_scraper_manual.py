"""Manually tests MapScraper by fetching pending map ingestion-state rows.

This helper bypasses controllers intentionally and is only for manual debugging.
"""

from cs2_analytics.ingestion_state import MapIngestionState
from cs2_analytics.scrapers.map_scraper import MapScraper

map_state = MapIngestionState()


def main():
    """Main test function for MapScraper."""
    print("Starting MapScraper manual test...")

    pending_maps = map_state.fetch(limit=3)
    if not pending_maps:
        print("No pending map links found. You may need to run MatchParser first.")
        return

    with MapScraper() as scraper:
        for pending_map in pending_maps:
            map_id = pending_map[0]
            map_url = pending_map[1]
            soup = scraper.fetch_soup(map_url)
            print(f"Scraped map {map_id} from {map_url}. Soup length: {len(soup.text)}")

    print(f"Finished scraping {len(pending_maps)} map(s).")


if __name__ == "__main__":
    main()
