"""Manual debug script: run scrape -> parse -> store for pending maps.

Usage: python scripts/debug_map_ingestion.py (requires a configured database
and browser dependencies).

This helper bypasses controllers intentionally and is only for manual debugging.
"""

from cs2_analytics.ingestion_state import MapIngestionState
from cs2_analytics.parsers.map_parser import MapParser
from cs2_analytics.scrapers.map_scraper import MapScraper
from cs2_analytics.storage.player_storage import store_players

map_state = MapIngestionState()


def main():
    print("Starting manual test for MapParser...")

    pending_maps = map_state.fetch(limit=1)
    if not pending_maps:
        print("No pending map pages found.")
        return

    parser = MapParser()
    total_players = []

    with MapScraper() as scraper:
        for pending_map in pending_maps:
            map_id = pending_map[0]
            map_url = pending_map[1]
            soup = scraper.fetch_soup(map_url)
            players = parser.parse_map(soup, map_url, map_id)
            if players:
                store_players(players)
                map_state.mark_as_processed(map_id)
                print(f"Parsed {len(players)} players from {map_url}")
                total_players.extend(players)
            else:
                map_state.mark_as_failed(map_id, "Map parser returned empty")
                print(f"Failed to parse {map_url}")

    if total_players:
        print(f"Example Player: {total_players[0]}")


if __name__ == "__main__":
    main()
