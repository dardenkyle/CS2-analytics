from pipeline.cs2_pipeline import CS2AnalyticsPipeline  # Import the pipeline class
import datetime as dt
from log_manager import setup_logger

logger = setup_logger(__name__)

def main() -> None:
    """Runs the full CS2 analytics pipeline."""
    logger.info("Starting script at: %s", dt.datetime.now())
    pipeline = CS2AnalyticsPipeline()
    pipeline.run()

if __name__ == "__main__":
    logger.info("🚀 Starting CS2 Analytics at %s", dt.datetime.now())
    main()