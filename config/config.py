"""
Configuration file for CS2 Analytics Pipeline.

This file centralizes all configurable settings, including:
- Database credentials
- Web scraping parameters
- File storage paths
- Logging settings
"""

import os
import datetime as dt
import logging
from dotenv import load_dotenv


# ✅ Load environment variables from `.env` file
load_dotenv()

# ✅ Database Configuration
DB_NAME = os.getenv("DB_NAME", default="default_db")
DB_USER = os.getenv("DB_USER", default="default_user")
DB_PASS = os.getenv("DB_PASS", default="default_pass")
DB_HOST = os.getenv("DB_HOST", default="localhost")
DB_PORT = os.getenv("DB_PORT", default="5432")

# Match Scraping Configuration
START_DATE = os.getenv(
    "START_DATE", default="2025-01-29"
)  # Default: Season 2 start date
END_DATE = os.getenv(
    "END_DATE", default=dt.datetime.now().strftime("%Y-%m-%d")
)  # Set in .env file, or defaults to today


# ✅ Feature Toggles (Convert to Boolean)
def str_to_bool(value: str) -> bool:
    """Converts environment string values to boolean."""
    return value.lower() in ("true", "1", "yes", "on")


ENABLE_DEMO_DOWNLOADS = str_to_bool(os.getenv("ENABLE_DEMO_DOWNLOADS", default="False"))
ENABLE_DATA_STORAGE = str_to_bool(os.getenv("ENABLE_DATA_STORAGE", default="False"))
ENABLE_ANALYTICS = str_to_bool(os.getenv("ENABLE_ANALYTICS", default="False"))

# ✅ Environment Type (dev, staging, production)
ENVIRONMENT = os.getenv("ENVIRONMENT", default="development").lower()

# ✅ Logging Configuration
HLTV_URL = "https://www.hltv.org/results"  # HLTV Results URL
MAX_MATCHES = int(
    os.getenv("MAX_MATCHES", default=1)
)  # Maximum number of matches to scrape
logging.info("MAX_MATCHES set to: %s", MAX_MATCHES)
DEBUG_MODE = os.getenv("DEBUG_MODE", default="False")  # Enable debug mode
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL, logging.DEBUG)  # Convert to actual log level
logging.basicConfig(level=LOG_LEVEL)  # ✅ Apply correct log level
print(
    f"🔍 [DEBUG] LOG_LEVEL from config: {LOG_LEVEL} (should be an integer, like 10 for DEBUG)"
)
LOG_FILE = os.path.join(os.getcwd(), "logs", "app.log")  # Log file path
logging.basicConfig(level=logging.DEBUG)
print(f"🔍 [DEBUG] LOG_LEVEL from config: {LOG_LEVEL}")
BATCH_SIZE = 1000

# ✅ Print Configuration on Startup (For Debugging)
logging.debug(
    f"""
🔧 CONFIGURATION LOADED:
-------------------------
🌍 ENVIRONMENT: {ENVIRONMENT}
📦 DATABASE: {DB_NAME} (Host: {DB_HOST}, Port: {DB_PORT})
⚙️ FEATURES:
   - Demo Downloads: {ENABLE_DEMO_DOWNLOADS}
   - Data Storage: {ENABLE_DATA_STORAGE}
   - Analytics: {ENABLE_ANALYTICS}
🛠️ LOG LEVEL: {LOG_LEVEL}
-------------------------
"""
)
