"""
Manually tests the MapScraper by scraping map pages from the queue
and printing confirmation of retrieved HTML content.
"""

from scrapers.map_scraper import MapScraper


def main():
    """Main test function for MapScraper."""
    print("🧪 Starting MapScraper manual test...")

    with MapScraper() as scraper:
        scraped = scraper.run(limit=3)

    if not scraped:
        print("⚠️ No queued map links found. You may need to run MatchParser first.")
        return

    for soup, map_id, map_url in scraped:
        print(f"✅ Scraped map {map_id} from {map_url} — Soup length: {len(soup.text)}")

    print(f"🏁 Finished scraping {len(scraped)} map(s).")


if __name__ == "__main__":
    main()
