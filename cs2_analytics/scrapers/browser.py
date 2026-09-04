"""Single construction path for the SeleniumBase browser used by scrapers.

Every scraper builds its driver here so display mode is decided in one
place (#194). Headless is the default and what the desktop runs. A
display-less Linux host that fails the source's stats-section challenge
can run headed under a virtual display instead
(`BROWSER_HEADLESS=false xvfb-run -a cs2a process ...`); see
docs/deployment.md, "Scrape Host Requirements".
"""

import os
import sys

from selenium.webdriver.remote.webdriver import WebDriver
from seleniumbase import Driver

from cs2_analytics.config.config import BROWSER_HEADLESS
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


def create_driver(headless: bool | None = None) -> WebDriver:
    """Starts an undetected-mode Chrome driver in the configured display mode.

    Args:
        headless: Overrides the `BROWSER_HEADLESS` setting when given.

    On Linux, SeleniumBase silently forces headless when `DISPLAY` is unset,
    so a headed request on a display-less host cannot be honored. That case
    is logged as a warning rather than raised: the fix is to wrap the
    process in `xvfb-run -a`, which provides the display.
    """
    use_headless = BROWSER_HEADLESS if headless is None else headless
    display = os.getenv("DISPLAY")

    if not use_headless and sys.platform.startswith("linux") and not display:
        logger.warning(
            "Headed browser requested but DISPLAY is unset; SeleniumBase will "
            "force headless mode. Run under `xvfb-run -a` to provide a display."
        )

    logger.info(
        "Starting browser (headless=%s, display=%s).",
        use_headless,
        display or "unset",
    )
    return Driver(uc=True, headless=use_headless)
