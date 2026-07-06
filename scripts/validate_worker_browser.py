"""Validate that the container worker can start Selenium/Chromium."""

import sys

from seleniumbase import Driver

from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

EXPECTED_TITLE = "CS2 Analytics Worker Browser Check"
CHECK_URL = (
    "data:text/html,"
    "<html><head><title>CS2 Analytics Worker Browser Check</title></head>"
    "<body>ok</body></html>"
)


def main() -> int:
    """Start Chromium through SeleniumBase and load a deterministic page."""
    driver = None
    try:
        driver = Driver(uc=True, headless=True)
        driver.get(CHECK_URL)
        if driver.title != EXPECTED_TITLE:
            raise RuntimeError(f"Unexpected browser check title: {driver.title!r}")
    except Exception as exc:
        logger.exception("Worker browser validation failed: %s", exc)
        return 1
    finally:
        if driver is not None:
            driver.quit()

    logger.info("Worker browser validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
