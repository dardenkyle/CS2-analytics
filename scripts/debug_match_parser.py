"""Manual debug script: fetch one live match page and log what MatchParser makes of it.

Usage: python scripts/debug_match_parser.py MATCH_URL

Opens no database connection and writes nothing to the database; the
shared logger still writes ./logs/app.log. Project configuration loads at
import, so the selected env file must name a local database host even
though none is contacted (the default dev environment does). Fetches the
page through MatchScraper, the same path the match stage uses, then logs
the parsed match and the map and demo links it found. Useful when the
source's markup changes and parser output needs a quick check against a
real page.
"""

import argparse

from cs2_analytics.parsers.match_parser import MatchParser
from cs2_analytics.scrapers.match_scraper import MatchScraper
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Fetch and parse one match page, logging the parsed result."""
    arg_parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    arg_parser.add_argument("match_url", help="Full URL of a match page.")
    args = arg_parser.parse_args()

    with MatchScraper() as scraper:
        soup = scraper.fetch_soup(args.match_url)

    match, map_links, demo_links = MatchParser().parse_match(soup, args.match_url)
    logger.info("Parsed match: %s", match)
    logger.info("Map links (%s): %s", len(map_links), map_links)
    logger.info("Demo links (%s): %s", len(demo_links), demo_links)


if __name__ == "__main__":
    main()
