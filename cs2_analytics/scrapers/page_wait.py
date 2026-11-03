"""Shared required-selector wait, challenge detection, and fetch timing.

The match and map scrapers load a page, wait for a selector that only a
rendered page contains, and hand the page source to their parser. When the
selector never appears within the wait, the page is either the source's
bot-challenge interstitial or an incomplete render; both are transient and
must surface as the retryable session error so the controller can rotate
the session and try again instead of recording a permanent parse failure.

A page counts as challenged when a challenge marker appears in its title,
or when the page is interstitial-sized and a marker appears in its visible
text (title and body with script, style, noscript, and template content
removed). A fully rendered page is hundreds of kilobytes; its scripts,
hidden forms, or user comments can mention "captcha" or "just a moment",
and such a page must be reported as missing content rather than as a
challenge (#260).
"""

import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from cs2_analytics.exceptions import SessionScrapeError
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

DEFAULT_CONTENT_WAIT_SECONDS = 10.0
PAGE_SNIPPET_LIMIT = 300
CHALLENGE_MARKERS = (
    "access denied",
    "captcha",
    "checking your browser",
    "cloudflare",
    "enable javascript",
    "just a moment",
    "verify you are human",
)
NON_VISIBLE_TAGS = ("script", "style", "noscript", "template")
# Measured page source (#260): a live challenge interstitial was 44,870
# characters; rendered results listings, a match page, and the home page
# were 281,271 to 439,508. Body-text markers only count at or below this
# length.
INTERSTITIAL_MAX_LENGTH = 100_000


def fetch_rendered_page(
    driver,
    url: str,
    required_selector: str,
    page_label: str,
    content_wait_seconds: float,
) -> str:
    """Loads a URL, waits for its required selector, and returns page source.

    Logs the fetch duration once the page has rendered so per-item timing is
    measurable across both scrapers. Raises `SessionScrapeError` when the
    selector does not appear within the wait.
    """
    started_at = time.perf_counter()
    driver.get(url)
    wait_for_required_content(
        driver,
        url,
        required_selector,
        page_label,
        content_wait_seconds,
    )
    elapsed_seconds = time.perf_counter() - started_at
    logger.info(
        "%s fetched url=%s elapsed_seconds=%.2f",
        page_label,
        url,
        elapsed_seconds,
    )
    return str(driver.page_source)


def wait_for_required_content(
    driver,
    requested_url: str,
    required_selector: str,
    page_label: str,
    content_wait_seconds: float,
) -> None:
    """Waits until the loaded page contains the required selector.

    On timeout, logs the diagnostic line with challenge-marker flags and
    raises `SessionScrapeError`, distinguishing a challenged page from a
    page that simply never rendered.
    """
    try:
        WebDriverWait(driver, content_wait_seconds).until(
            lambda current_driver: current_driver.find_element(
                By.CSS_SELECTOR,
                required_selector,
            )
        )
    except TimeoutException as e:
        marker_flags = log_missing_content(
            driver,
            requested_url,
            required_selector,
            page_label,
        )
        challenge_markers = [
            marker for marker, is_present in marker_flags.items() if is_present
        ]
        if challenge_markers:
            marker_list = ", ".join(challenge_markers)
            raise SessionScrapeError(
                f"{page_label} appears blocked or challenged "
                f"after {content_wait_seconds:g}s "
                f"(markers: {marker_list}): {requested_url}"
            ) from e
        raise SessionScrapeError(
            f"{page_label} missing required content "
            f"after {content_wait_seconds:g}s: {requested_url}"
        ) from e


def normalized_text(soup: BeautifulSoup) -> str:
    """Return the soup's text lowercased with whitespace collapsed.

    Text is joined with a space at every tag boundary, so a word split by
    inline markup (`Ver<b>ify</b>`) reads as two words.
    """
    return " ".join(soup.get_text(" ").split()).lower()


def challenge_marker_flags(page_source: str) -> dict[str, bool]:
    """Return one flag per challenge marker for a page that lacks its selector.

    A marker counts when it is in the page title, at any page size, or in
    the visible text of a page no longer than `INTERSTITIAL_MAX_LENGTH`.
    Visible text drops script, style, noscript, and template content;
    attribute values are never part of it. Text hidden by CSS and user
    content still count as visible, which is why the size gate is needed.
    """
    soup = BeautifulSoup(page_source, "html.parser")
    title_text = normalized_text(soup.title) if soup.title else ""
    searched_text = title_text
    if len(page_source) <= INTERSTITIAL_MAX_LENGTH:
        for tag in soup(NON_VISIBLE_TAGS):
            tag.decompose()
        searched_text = normalized_text(soup)
    return {
        marker.replace(" ", "_"): marker in searched_text
        for marker in CHALLENGE_MARKERS
    }


def log_missing_content(
    driver,
    requested_url: str,
    required_selector: str,
    page_label: str,
) -> dict[str, bool]:
    """Logs page diagnostics for a missing selector and returns marker flags.

    The flags come from `challenge_marker_flags`, so they mark a challenge
    interstitial, not a rendered page that mentions the same words.
    """
    page_source = driver.page_source or ""
    marker_flags = challenge_marker_flags(page_source)
    snippet = " ".join(page_source.split())[:PAGE_SNIPPET_LIMIT]

    logger.warning(
        "%s missing required selector=%s requested_url=%s "
        "current_url=%s title=%s page_source_length=%d marker_flags=%s "
        "page_snippet=%r",
        page_label,
        required_selector,
        requested_url,
        getattr(driver, "current_url", None),
        getattr(driver, "title", None),
        len(page_source),
        marker_flags,
        snippet,
    )
    return marker_flags
