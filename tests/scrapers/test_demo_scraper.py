from scrapers.demo_scraper import DemoScraper

# ✅ Replace this with a real HLTV demo link
demo_url = "https://www.hltv.org/download/demo/95241"

scraper = DemoScraper()

# ✅ Step 1: Download demo into RAM
archive_buffer = scraper.download_demo_in_memory(demo_url)

if archive_buffer:
    # ✅ Step 2: Extract demo in memory
    extracted_data = scraper.extract_demo_in_memory(archive_buffer)

    if extracted_data:
        # ✅ Step 3: Parse demo data
        scraper.process_demo(extracted_data)
