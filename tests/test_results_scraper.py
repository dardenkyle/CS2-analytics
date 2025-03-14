import unittest
from scrapers.results_scraper import ResultsScraper

class TestResultsScraper(unittest.TestCase):
    """Unit tests for verifying the ResultsScraper functionality."""

    @classmethod
    def setUpClass(cls):
        """Runs before all tests to initialize the scraper."""
        print("\n🚀 Setting up ResultsScraper for testing...")
        cls.scraper = ResultsScraper()

    def test_fetch_results(self):
        """Tests that match links are correctly extracted from HLTV."""
        print("\n🟢 Running test_fetch_results...")

        match_links = self.scraper.fetch_results(max_matches=3)  # ✅ Fetch 3 match links

        # ✅ Check if we got at least 1 match link
        self.assertGreater(len(match_links), 0, "❌ No match links were extracted!")

        # ✅ Ensure all extracted URLs are valid HLTV match URLs
        for link in match_links:
            self.assertTrue(link.startswith("https://www.hltv.org/matches/"), f"❌ Invalid match link: {link}")

        print(f"✅ Extracted match links: {match_links}")

    @classmethod
    def tearDownClass(cls):
        """Runs after all tests to close the scraper."""
        print("\n🛑 Closing ResultsScraper...")
        cls.scraper.close()

if __name__ == "__main__":
    print("\n🔵 Running ResultsScraper tests...\n")
    unittest.main()
