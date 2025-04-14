"""
Manually tests MatchParser by scraping a real HLTV match page
using SeleniumBase and parsing it into a Match object.

This test:
- Launches a headless browser using SeleniumBase
- Navigates to a real HLTV match page
- Parses the page using MatchParser
- Prints the Match object and queues demo/map links
"""

from seleniumbase import Driver
from bs4 import BeautifulSoup
from parsers.match_parser import MatchParser


def main():
    """Main test for MatchParser using SeleniumBase."""
    match_url = "https://www.hltv.org/matches/2381532/sangal-vs-fire-flux-galaxy-battle-2025-phase-1"

    driver = Driver(uc=True, headless=True)
    try:
        print("🌐 Fetching HLTV match page...")
        driver.get(match_url)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        print("🔍 Parsing match with MatchParser...")
        parser = MatchParser()
        match = parser.parse_match(soup, match_url)

        if match:
            print("✅ MatchParser succeeded:")
            print(match)
        else:
            print("❌ MatchParser returned None.")

    finally:
        driver.quit()
        print("🚪 Browser closed.")


if __name__ == "__main__":
    main()
