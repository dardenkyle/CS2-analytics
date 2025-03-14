import io
import os
import time
import rarfile
import zipfile
from seleniumbase import Driver
from selenium.webdriver.chrome.options import Options
from utils.log_manager import get_logger
from parsers.demo_parser import DemoParser

logger = get_logger(__name__)

class DemoScraper:
    """Handles downloading and extracting HLTV match demos using SeleniumBase."""

    def __init__(self, download_dir="demos/"):
        """
        Initializes SeleniumBase driver with custom download settings.

        Args:
            download_dir (str): Path to store temporary downloaded files.
        """
        self.download_dir = os.path.abspath(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)  # ✅ Ensure download folder exists

        # ✅ Set Chrome download preferences
        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": self.download_dir,  # ✅ Auto-download to this folder
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })

        # ✅ Use `Driver()` correctly (DO NOT use `options=chrome_options`)
        self.driver = Driver(uc=True, headless=True)  # ✅ No options argument
        self.demo_parser = DemoParser()

    def download_demo_in_memory(self, demo_url):
        """
        Uses SeleniumBase to download the demo archive, waits for completion, and loads it into RAM.

        Args:
            demo_url (str): The HLTV demo download URL.

        Returns:
            io.BytesIO | None: Memory buffer containing the downloaded archive.
        """
        try:
            logger.info(f"🌐 Navigating to demo URL: {demo_url}")
            self.driver.get(demo_url)
            time.sleep(5)  # ✅ Allow time for download

            # ✅ Get the most recently downloaded file
            demo_file = self._get_latest_downloaded_file()
            if not demo_file:
                logger.error("❌ No demo file detected in download folder.")
                return None

            # ✅ Read the file into RAM
            with open(demo_file, "rb") as f:
                archive_buffer = io.BytesIO(f.read())

            logger.info(f"✅ Demo archive loaded into memory: {demo_file}")

            # ✅ Delete the file after reading to prevent disk clutter
            os.remove(demo_file)
            return archive_buffer

        except Exception as e:
            logger.error(f"❌ Failed to download demo: {e}")
            return None

    def _get_latest_downloaded_file(self):
        """Returns the most recently downloaded file in the configured directory."""
        try:
            files = [os.path.join(self.download_dir, f) for f in os.listdir(self.download_dir)]
            if not files:
                return None
            return max(files, key=os.path.getctime)  # ✅ Get most recent file
        except Exception as e:
            logger.error(f"❌ Error retrieving downloaded file: {e}")
            return None

    def extract_demo_in_memory(self, archive_buffer):
        """
        Extracts demo files from a RAR or ZIP archive in RAM.

        Args:
            archive_buffer (io.BytesIO): Memory buffer containing the archive.

        Returns:
            dict | None: Dictionary containing extracted demo filenames and their content.
        """
        extracted_files = {}

        try:
            if zipfile.is_zipfile(archive_buffer):
                with zipfile.ZipFile(archive_buffer) as archive:
                    for file_name in archive.namelist():
                        with archive.open(file_name) as file:
                            extracted_files[file_name] = file.read()  # ✅ Store in memory

            elif rarfile.is_rarfile(archive_buffer):
                with rarfile.RarFile(archive_buffer) as archive:
                    for file_name in archive.namelist():
                        with archive.open(file_name) as file:
                            extracted_files[file_name] = file.read()  # ✅ Store in memory
            else:
                logger.warning("⚠️ Unsupported file format.")
                return None

            logger.info(f"✅ Extracted {len(extracted_files)} demo files into memory.")
            return extracted_files

        except Exception as e:
            logger.error(f"❌ Error extracting demo in memory: {e}")
            return None

    def process_demo(self, demo_data):
        """
        Passes extracted demo data to the DemoParser.

        Args:
            demo_data (dict): Extracted demo filenames and their content.
        """
        if not demo_data:
            logger.warning("⚠️ No demo data to process.")
            return

        logger.info(f"📊 Passing {len(demo_data)} demo files to parser...")
        self.demo_parser.parse_demos(demo_data)  # ✅ Send to parser

    def close(self):
        """Closes SeleniumBase driver."""
        self.driver.quit()
        logger.info("🚪 Selenium driver closed.")