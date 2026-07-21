"""Tests for the worker browser validation script diagnostics (issue #91)."""

import subprocess

import pytest

import scripts.validate_worker_browser as validate_module
from scripts.validate_worker_browser import (
    get_binary_version,
    get_package_version,
    log_browser_stack_versions,
)


class FakeCompletedProcess:
    def __init__(self, stdout: str = "", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_get_binary_version_reports_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr(validate_module.shutil, "which", lambda _binary: None)

    assert get_binary_version("chromium") == "not found"


def test_get_binary_version_prefers_stdout(monkeypatch) -> None:
    monkeypatch.setattr(
        validate_module.shutil, "which", lambda _binary: "/usr/bin/chromium"
    )
    monkeypatch.setattr(
        validate_module.subprocess,
        "run",
        lambda *_args, **_kwargs: FakeCompletedProcess(stdout="Chromium 150.0\n"),
    )

    assert get_binary_version("chromium") == "Chromium 150.0"


def test_get_binary_version_falls_back_to_stderr(monkeypatch) -> None:
    monkeypatch.setattr(
        validate_module.shutil, "which", lambda _binary: "/usr/bin/chromedriver"
    )
    monkeypatch.setattr(
        validate_module.subprocess,
        "run",
        lambda *_args, **_kwargs: FakeCompletedProcess(stderr="ChromeDriver 150.0\n"),
    )

    assert get_binary_version("chromedriver") == "ChromeDriver 150.0"


def test_get_binary_version_reports_command_failure(monkeypatch) -> None:
    def raise_timeout(*args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=30)

    monkeypatch.setattr(
        validate_module.shutil, "which", lambda _binary: "/usr/bin/chromium"
    )
    monkeypatch.setattr(validate_module.subprocess, "run", raise_timeout)

    assert get_binary_version("chromium").startswith("version check failed:")


def test_get_package_version_reports_installed_package() -> None:
    assert get_package_version("pytest") == pytest.__version__


def test_get_package_version_reports_missing_package() -> None:
    assert get_package_version("definitely-not-a-real-package") == "not installed"


def test_log_browser_stack_versions_logs_all_components(monkeypatch, caplog) -> None:
    monkeypatch.setattr(validate_module, "get_binary_version", lambda _binary: "1.2.3")
    monkeypatch.setattr(
        validate_module, "get_package_version", lambda _package: "4.5.6"
    )

    logger = validate_module.logger
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level("INFO", logger=logger.name):
            log_browser_stack_versions()
    finally:
        logger.removeHandler(caplog.handler)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    for component in ("chromium", "chromedriver", "seleniumbase", "selenium"):
        assert component in logged
