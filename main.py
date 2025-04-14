"""Main entry point for the CS2 Analytics pipeline."""

from cs2_analytics.pipeline.cs2_pipeline import CS2AnalyticsPipeline
from cs2_analytics.utils.log_manager import get_logger
import datetime as dt

logger = get_logger(__name__)
logger.info("🚀 Starting CS2 Analytics Pipeline at %s", dt.datetime.now())

def main() -> None:
    pipeline = CS2AnalyticsPipeline()
    pipeline.run()

if __name__ == "__main__":
    main()
