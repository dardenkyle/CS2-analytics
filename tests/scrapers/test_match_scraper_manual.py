"""Manually tests MatchScraper + MatchParser integration from queued matches."""

from cs2_analytics.parsers.match_parser import MatchParser
from cs2_analytics.queues import match_queue
from cs2_analytics.scrapers.match_scraper import MatchScraper
from cs2_analytics.storage.match_storage import store_matches


def main():
    """Main test for MatchScraper + MatchParser integration."""
    print("Testing MatchScraper + MatchParser integration...")

    queued_matches = match_queue.fetch(limit=3)
    if not queued_matches:
        print("No queued matches found. Run the results scraper first.")
        return

    parser = MatchParser()
    parsed_matches = []

    with MatchScraper() as scraper:
        for match_id, match_url in queued_matches:
            print(f"Parsing {match_url}")
            soup = scraper.fetch_soup(match_url)
            match_obj, _, _ = parser.parse_match(soup, match_url)

            if match_obj:
                parsed_matches.append(match_obj)
                store_matches([match_obj])
                match_queue.mark_as_parsed(match_id)
                print(f"Stored match {match_id}")
            else:
                match_queue.mark_as_failed(match_id, "Parser returned None")
                print(f"Failed to parse match {match_id}")

    print(f"Completed. Parsed: {len(parsed_matches)} matches.")


if __name__ == "__main__":
    main()
