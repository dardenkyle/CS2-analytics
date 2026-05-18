"""Manually tests MapParser from queued map pages.

This helper bypasses controllers intentionally and is only for manual debugging.
"""

from cs2_analytics.ingestion_state import MapIngestionState
from cs2_analytics.parsers.map_parser import MapParser
from cs2_analytics.scrapers.map_scraper import MapScraper
from cs2_analytics.storage.player_storage import store_players

map_queue = MapIngestionState()


def main():
    print("Starting manual test for MapParser...")

    queued_maps = map_queue.fetch(limit=1)
    if not queued_maps:
        print("No map pages in queue.")
        return

    parser = MapParser()
    total_players = []

    with MapScraper() as scraper:
        for queued_map in queued_maps:
            map_id = queued_map[0]
            map_url = queued_map[1]
            soup = scraper.fetch_soup(map_url)
            players = parser.parse_map(soup, map_url, map_id)
            if players:
                store_players(players)
                map_queue.mark_as_processed(map_id)
                print(f"Parsed {len(players)} players from {map_url}")
                total_players.extend(players)
            else:
                map_queue.mark_as_failed(map_id, "Map parser returned empty")
                print(f"Failed to parse {map_url}")

    if total_players:
        print(f"Example Player: {total_players[0]}")


if __name__ == "__main__":
    main()
