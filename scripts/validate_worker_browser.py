"""Validate that the container worker can start Selenium/Chromium."""

import shutil
import subprocess
import sys
from importlib import metadata

from seleniumbase import Driver

from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

EXPECTED_TITLE = "CS2 Analytics Worker Browser Check"
CHECK_URL = (
    "data:text/html,"
    "<html><head><title>CS2 Analytics Worker Browser Check</title></head>"
    "<body>ok</body></html>"
)
BROWSER_BINARIES = ("chromium", "chromedriver")
BROWSER_PACKAGES = ("seleniumbase", "selenium")
VERSION_COMMAND_TIMEOUT_SECONDS = 30


def get_binary_version(binary: str) -> str:
    """Return the ``--version`` output for a browser binary on PATH."""
    path = shutil.which(binary)
    if path is None:
        return "not found"
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=VERSION_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"version check failed: {exc}"
    return result.stdout.strip() or result.stderr.strip() or "unknown"


def get_package_version(package: str) -> str:
    """Return the installed version of a Python package."""
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not installed"


def log_browser_stack_versions() -> None:
    """Log browser stack versions so failures are attributable to drift."""
    for binary in BROWSER_BINARIES:
        logger.info("Browser stack: %s %s", binary, get_binary_version(binary))
    for package in BROWSER_PACKAGES:
        logger.info("Browser stack: %s %s", package, get_package_version(package))


def main() -> int:
    """Start Chromium through SeleniumBase and load a deterministic page."""
    log_browser_stack_versions()
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
