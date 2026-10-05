"""Stub driver and wait used by the match and map scraper tests.

The fakes stand in for SeleniumBase's driver and Selenium's `WebDriverWait`
so the required-selector wait can be exercised without a browser.
"""

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException

MAX_POLLS = 5


class FakeDriver:
    """Records page loads and answers selector lookups from a fixed page.

    `renders_after_polls` controls how many lookups fail before the page
    counts as rendered; `None` means it never renders. Once rendered, a
    lookup succeeds only if the selector matches the page source.
    """

    def __init__(
        self,
        page_source: str,
        *,
        renders_after_polls: int | None = 0,
    ) -> None:
        self.page_source = page_source
        self.renders_after_polls = renders_after_polls
        self.current_url = "about:blank"
        self.title = "fake page"
        self.loaded_urls: list[str] = []
        self.find_calls: list[tuple[str, str]] = []
        self.quit_called = False

    def get(self, url: str) -> None:
        self.loaded_urls.append(url)
        self.current_url = url

    def find_element(self, by: str, selector: str) -> object:
        self.find_calls.append((by, selector))
        polls_so_far = len(self.find_calls)
        if (
            self.renders_after_polls is not None
            and polls_so_far > self.renders_after_polls
        ):
            soup = BeautifulSoup(self.page_source, "html.parser")
            element = soup.select_one(selector)
            if element is not None:
                return element
        raise TimeoutException("missing required content")

    def quit(self) -> None:
        self.quit_called = True


class FakePollingWait:
    """Polls the condition a bounded number of times, like `WebDriverWait`."""

    def __init__(self, driver: FakeDriver, _timeout: float) -> None:
        self.driver = driver

    def until(self, condition) -> object:
        last_error: Exception | None = None
        for _ in range(MAX_POLLS):
            try:
                return condition(self.driver)
            except Exception as exc:
                last_error = exc
        raise TimeoutException("condition timed out") from last_error
