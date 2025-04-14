from scrapers.map_scraper import MapScraper
from parsers.map_parser import MapParser
from storage import db, map_queue


def main():
    print("🧪 Starting manual test for MapParser...")

    with MapScraper() as scraper:
        map_soups = scraper.run(limit=1)

    if not map_soups:
        print("⚠️ No map pages in queue.")
        return

    parser = MapParser()
    total_players = []

    for soup, map_id, map_url in map_soups:
        players = parser.parse_map(soup, map_url, match_id=2381532)  # use real match_id
        if players:
            db.store_players(players)  # ✅ <--- THIS STORES THE DATA
            map_queue.mark_parsed(map_id)
            print(f"✅ Parsed {len(players)} players from {map_url}")
            total_players.extend(players)
        else:
            map_queue.mark_failed(map_id, "Map parser returned empty")
            print(f"❌ Failed to parse {map_url}")

    if total_players:
        print(f"🔍 Example Player: {total_players[0]}")


if __name__ == "__main__":
    main()
