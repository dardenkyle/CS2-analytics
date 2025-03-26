"""Main entry point for the CS2 Analytics pipeline."""

import datetime as dt
from pipeline.cs2_pipeline import CS2AnalyticsPipeline
from utils.log_manager import get_logger
from config.config import LOG_LEVEL

logger = get_logger(__name__)
logger.setLevel(LOG_LEVEL)  # ✅ Explicitly override any previous incorrect level

print(f"🔍 [DEBUG] Logger Level in Main: {logger.level}")  # Should be 10 (DEBUG)

if not logger.hasHandlers():
    print("⚠️ No handlers found in Main!")
else:
    for handler in logger.handlers:
        print(f"🛠️ Handler: {handler}, Level: {handler.level}")

print("🟡 Attempting to log messages...")

logger.debug("🔵 Debug log from Main.")
logger.info("🟢 Info log from Main.")
logger.warning("🟡 Warning log from Main.")
logger.error("🔴 Error log from Main.")

print("🟢 Finished logging.")


def main() -> None:
    """Runs the full CS2 analytics pipeline."""
    logger.info("🚀 Starting CS2 Analytics Pipeline at %s", dt.datetime.now())
    print("testing this print in main.....")
    pipeline = CS2AnalyticsPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
