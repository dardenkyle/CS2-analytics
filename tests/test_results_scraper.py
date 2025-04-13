import sys
import os
from scrapers.results_scraper import ResultsScraper

# ✅ Absolute path to your project root (edit this if needed)
project_root = r"C:\Users\Kyle\Desktop\projects\CS2 analytics"
if project_root not in sys.path:
    sys.path.insert(0, project_root)


scraper = ResultsScraper()

try:
    scraper.run(max_matches=10)
finally:
    scraper.close()
