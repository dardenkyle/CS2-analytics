"""Main entry point for the CS2 Analytics pipeline."""

import datetime as dt
from pipeline.cs2_pipeline import CS2AnalyticsPipeline
from utils.log_manager import get_logger

logger = get_logger(__name__)
logger.info("🚀 Starting CS2 Analytics Pipeline at %s", dt.datetime.now())


def main() -> None:
    """Runs the full CS2 analytics pipeline."""
    pipeline = CS2AnalyticsPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
