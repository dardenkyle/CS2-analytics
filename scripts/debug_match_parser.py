"""Manual debug script: parse a single live match page with MatchParser.

Usage: python scripts/debug_match_parser.py (no database required; edit
match_url to target a different page). Launches a headless SeleniumBase
browser, fetches the page, parses it, and prints the result. Useful when
the upstream markup changes and parser output needs a quick check.
"""

from bs4 import BeautifulSoup
from seleniumbase import Driver

from cs2_analytics.parsers.match_parser import MatchParser


def main():
    """Fetch and parse one match page, printing the parser result."""
    match_url = "https://www.hltv.org/matches/2381532/sangal-vs-fire-flux-galaxy-battle-2025-phase-1"

    driver = Driver(uc=True, headless=True)
    try:
        print("Fetching HLTV match page...")
        driver.get(match_url)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        print("Parsing match with MatchParser...")
        parser = MatchParser()
        match = parser.parse_match(soup, match_url)

        if match:
            print("MatchParser succeeded:")
            print(match)
        else:
            print("MatchParser returned None.")

    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    main()
