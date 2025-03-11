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

# ✅ **HLTV Scraper Configuration**
HLTV_URL = "https://www.hltv.org/results"
MAX_MATCHES = 1  # Set limit for match scraping (adjust as needed)

# ✅ **Demo Download & Storage**
DEMO_STORAGE_PATH = os.path.join(os.getcwd(), "demos")  # Local storage for demo files

# ✅ **Database Configuration**
DB_NAME = os.getenv("CS2_DB_NAME", "cs2_db")   # Uses environment variable or default
DB_USER = os.getenv("CS2_DB_USER", "your_user")
DB_PASS = os.getenv("CS2_DB_PASS", "your_password")
DB_HOST = os.getenv("CS2_DB_HOST", "localhost")
DB_PORT = os.getenv("CS2_DB_PORT", "5432")

# ✅ **Logging Configuration**
LOG_FILE = os.path.join(os.getcwd(), "logs", "app.log")  # Log file path
LOG_LEVEL = "INFO"  # Available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

# ✅ **Scheduling & Execution**
RUN_INTERVAL = dt.timedelta(hours=6)  # Defines how often the scraper runs (e.g., every 6 hours)

# ✅ **Feature Flags (Enable/Disable Components)**
ENABLE_DEMO_DOWNLOADS = True  # Set to False to disable demo downloading
ENABLE_DATA_STORAGE = True  # Set to False to disable database inserts
ENABLE_ANALYTICS = True  # Set to False to disable analytics processing
