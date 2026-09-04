"""Tests for the shared scraper browser construction path (#194)."""

import pytest

from cs2_analytics.scrapers import browser as browser_module
from cs2_analytics.scrapers.browser import create_driver


class _RecordingDriver:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


@pytest.fixture
def driver_kwargs(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_driver(**kwargs):
        captured.update(kwargs)
        return _RecordingDriver(**kwargs)

    monkeypatch.setattr(browser_module, "Driver", fake_driver)
    return captured


def test_defaults_to_configured_headless_mode(
    monkeypatch: pytest.MonkeyPatch, driver_kwargs: dict[str, object]
) -> None:
    monkeypatch.setattr(browser_module, "BROWSER_HEADLESS", False)
    monkeypatch.setenv("DISPLAY", ":99")

    create_driver()

    assert driver_kwargs == {"uc": True, "headless": False}


def test_explicit_headless_overrides_config(
    monkeypatch: pytest.MonkeyPatch, driver_kwargs: dict[str, object]
) -> None:
    monkeypatch.setattr(browser_module, "BROWSER_HEADLESS", False)

    create_driver(headless=True)

    assert driver_kwargs == {"uc": True, "headless": True}


def test_headed_without_display_on_linux_warns(
    monkeypatch: pytest.MonkeyPatch,
    driver_kwargs: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(browser_module.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)

    logger = browser_module.logger
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level("WARNING", logger=logger.name):
            create_driver(headless=False)
    finally:
        logger.removeHandler(caplog.handler)

    assert any("xvfb-run" in record.getMessage() for record in caplog.records)
    assert driver_kwargs["headless"] is False


def test_headless_without_display_does_not_warn(
    monkeypatch: pytest.MonkeyPatch,
    driver_kwargs: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(browser_module.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)

    logger = browser_module.logger
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level("WARNING", logger=logger.name):
            create_driver(headless=True)
    finally:
        logger.removeHandler(caplog.handler)

    assert not [r for r in caplog.records if r.levelname == "WARNING"]
    assert driver_kwargs["headless"] is True
