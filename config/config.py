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
from utils.log_manager import get_logger

logger = logging.getLogger(__name__)

# ✅ Load environment variables from `.env` file
load_dotenv()

# ✅ Database Configuration
DB_NAME = os.getenv("DB_NAME", default="cs2_db")
DB_USER = os.getenv("DB_USER", default="postgres")
DB_PASS = os.getenv("DB_PASS", default="password")
DB_HOST = os.getenv("DB_HOST", default="localhost")
DB_PORT = os.getenv("DB_PORT", default="5432")
BATCH_SIZE = 1000  # Number of rows to insert in a single batch


# Feature Toggles
ENABLE_DATA_STORAGE = True
ENABLE_DEMO_DOWNLOADS = False
ENABLE_ANALYTICS = False

# Scraping Config
HLTV_URL = "https://www.hltv.org/results"  # HLTV Results URL
START_DATE = "2025-03-12"
END_DATE = "2025-03-12"
MAX_MATCHES = 1

# Debugging Mode
DEBUG_MODE = True

# Logging Config
LOG_LEVEL = logging.INFO
if DEBUG_MODE:
    LOG_LEVEL = logging.DEBUG
LOG_FILE = os.path.join(os.getcwd(), "logs", "app.log")


# ✅ Environment Type (dev, staging, production)
ENVIRONMENT = os.getenv("ENVIRONMENT", default="development").lower()
print(ENVIRONMENT)

# Log file path
logging.basicConfig(level=logging.DEBUG)
print(f"🔍 [DEBUG] LOG_LEVEL from config: {LOG_LEVEL}")


# ✅ Print Configuration on Startup (For Debugging)
logging.debug(
    """
🔧 CONFIGURATION LOADED:
-------------------------
🌍 ENVIRONMENT: %s
📦 DATABASE: %s (Host: %s, Port: %s)
⚙️ FEATURES:
   - Demo Downloads: %s
   - Data Storage: %s
   - Analytics: %s
🛠️ LOG LEVEL: %s
-------------------------
""",
    ENVIRONMENT,
    DB_NAME,
    DB_HOST,
    DB_PORT,
    ENABLE_DEMO_DOWNLOADS,
    ENABLE_DATA_STORAGE,
    ENABLE_ANALYTICS,
    LOG_LEVEL,
)
