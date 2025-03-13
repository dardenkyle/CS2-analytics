import os
import requests
from concurrent.futures import ThreadPoolExecutor
from log_manager.logger_config import setup_logger

logger = setup_logger(__name__)

class DemoScraper:
    """Handles downloading demo files from HLTV."""

    def __init__(self, demo_dir: str = "demos/"):
        """
        Initializes the demo scraper.

        Args:
            demo_dir (str): Directory where demo files will be stored.
        """
        self.demo_dir = demo_dir
        os.makedirs(self.demo_dir, exist_ok=True)

    def download_demos(self, match_list: list, max_threads: int = 4):
        """
        Downloads demo files for given matches.

        Args:
            match_list (list): List of matches with demo URLs.
            max_threads (int): Number of concurrent downloads.
        """
        if not match_list:
            logger.warning("⚠️ No matches provided for demo download.")
            return

        logger.info(f"📥 Starting demo downloads for {len(match_list)} matches...")

        with ThreadPoolExecutor(max_threads) as executor:
            executor.map(self._download_single_demo, match_list)

        logger.info("✅ All demo downloads completed.")

    def _download_single_demo(self, match: dict):
        """
        Downloads a single demo file.

        Args:
            match (dict): Match dictionary containing 'match_id' and 'demo_url'.
        """
        match_id = match.get("match_id")
        demo_url = match.get("demo_url")

        if not demo_url:
            logger.warning(f"⚠️ No demo URL available for match {match_id}. Skipping...")
            return

        file_name = f"{match_id}.dem"
        file_path = os.path.join(self.demo_dir, file_name)

        if os.path.exists(file_path):
            logger.info(f"🔄 Demo {file_name} already exists. Skipping download.")
            return

        try:
            logger.info(f"📥 Downloading demo: {demo_url} -> {file_path}")

            response = requests.get(demo_url, stream=True, timeout=15)
            response.raise_for_status()  # Raise an error for failed requests

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            logger.info(f"✅ Successfully downloaded: {file_name}")

        except requests.RequestException as e:
            logger.error(f"❌ Failed to download demo for match {match_id}: {e}")

