from pipeline.cs2_pipeline import CS2AnalyticsPipeline
import datetime as dt
from utils.log_manager import get_logger

logger = get_logger(__name__)

def main() -> None:
    """Runs the full CS2 analytics pipeline."""
    pipeline = CS2AnalyticsPipeline()
    pipeline.run()

if __name__ == "__main__":
    logger.info("🚀 Starting CS2 Analytics Pipeline at %s", dt.datetime.now())
    main()