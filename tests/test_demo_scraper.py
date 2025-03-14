from scraping.demo_scraper import DemoScraper

# ✅ Example match demo URL (Replace with real HLTV link)
test_demo_url = "https://www.hltv.org/download/demo/95240"
test_match_id = 95240

scraper = DemoScraper()
archive_path = scraper.download_demo(test_demo_url, test_match_id)

if archive_path:
    extracted_path = scraper.extract_demo(archive_path)
    print(f"\n🔍 Extracted Demo Files Path: {extracted_path}")