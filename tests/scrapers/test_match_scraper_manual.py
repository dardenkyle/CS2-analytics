"""
Manually tests the refactored MatchScraper by pulling soups from the queue.
"""

from cs2_analytics.parsers.match_parser import MatchParser
from cs2_analytics.queues import match_queue
from cs2_analytics.scrapers.match_scraper import MatchScraper
from cs2_analytics.storage.match_storage import store_matches


def main():
    """Main test for MatchScraper + MatchParser integration."""
    print("🚀 Testing MatchScraper + MatchParser integration...")

    with MatchScraper() as scraper:
        match_soups = scraper.run(limit=3)

    if not match_soups:
        print("⚠️ No queued matches found. Run the results scraper first.")
        return

    parser = MatchParser()
    parsed_matches = []

    for soup, match_id, match_url in match_soups:
        print(f"🔍 Parsing {match_url}")
        match = parser.parse_match(soup, match_url)
        if match:
            parsed_matches.append(match)
            store_matches([match])
            match_queue.mark_parsed(match_id)
            print(f"✅ Stored match {match_id}")
        else:
            match_queue.mark_failed(match_id, "Parser returned None")
            print(f"❌ Failed to parse match {match_id}")

    print(f"🏁 Completed. Parsed: {len(parsed_matches)} matches.")


if __name__ == "__main__":
    main()
