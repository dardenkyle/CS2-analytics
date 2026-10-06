"""The `cs2a` entry point applies --env before the CLI is imported."""

import sys

import pytest

from cs2_analytics import entrypoint
from cs2_analytics.exceptions import ConfigurationError
from cs2_analytics.runtime_env import ENV_SELECTOR_VAR


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--env", "prod", "status"], "prod"),
        (["--env=test", "status"], "test"),
        (["status"], None),
        (["--env"], None),
        (["--", "--env", "prod"], None),
        (["--env", "staging", "status"], "staging"),
    ],
)
def test_requested_environment_reads_both_option_spellings(
    argv: list[str], expected: str | None
) -> None:
    assert entrypoint.requested_environment(argv) == expected


def _run_main(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> list[str]:
    """Runs main() against a stub CLI module and returns the stub's calls."""
    calls: list[str] = []
    stub_cli = type(sys)("cs2_analytics.cli")
    stub_cli.app = lambda: calls.append("app")
    monkeypatch.setitem(sys.modules, "cs2_analytics.cli", stub_cli)
    monkeypatch.setattr(sys, "argv", ["cs2a", *argv])
    entrypoint.main()
    return calls


def test_main_exports_the_selected_environment_before_running_the_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ENV_SELECTOR_VAR, raising=False)

    calls = _run_main(monkeypatch, ["--env", "prod", "status"])

    assert entrypoint.os.environ[ENV_SELECTOR_VAR] == "prod"
    assert calls == ["app"]


def test_main_leaves_the_selector_alone_without_the_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_SELECTOR_VAR, "test")

    calls = _run_main(monkeypatch, ["status"])

    assert entrypoint.os.environ[ENV_SELECTOR_VAR] == "test"
    assert calls == ["app"]


def test_main_does_not_export_an_unknown_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_SELECTOR_VAR, "test")

    _run_main(monkeypatch, ["--env", "staging", "status"])

    # Typer rejects the value with a usage error; configuration must not
    # fail first on a selector the entry point wrote itself.
    assert entrypoint.os.environ[ENV_SELECTOR_VAR] == "test"


def test_main_reports_a_configuration_error_raised_while_the_app_runs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _app() -> None:
        raise ConfigurationError("The dev environment resolved DB_HOST.")

    stub_cli = type(sys)("cs2_analytics.cli")
    stub_cli.app = _app
    monkeypatch.setitem(sys.modules, "cs2_analytics.cli", stub_cli)
    monkeypatch.setattr(sys, "argv", ["cs2a", "status"])

    # A command that loads configuration lazily fails inside the app, not
    # at import; it must get the same one-line report.
    with pytest.raises(SystemExit) as exit_info:
        entrypoint.main()

    assert exit_info.value.code == entrypoint.CONFIGURATION_ERROR_EXIT_CODE
    assert "Configuration error: The dev environment" in capsys.readouterr().err


def test_main_reports_a_configuration_error_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class _FailingImport:
        def find_spec(self, name: str, *_args: object) -> None:
            if name == "cs2_analytics.cli":
                raise ConfigurationError("The dev environment resolved DB_HOST.")

    monkeypatch.delitem(sys.modules, "cs2_analytics.cli", raising=False)
    monkeypatch.setattr(sys, "meta_path", [_FailingImport(), *sys.meta_path])
    monkeypatch.setattr(sys, "argv", ["cs2a", "status"])

    with pytest.raises(SystemExit) as exit_info:
        entrypoint.main()

    assert exit_info.value.code == entrypoint.CONFIGURATION_ERROR_EXIT_CODE
    assert "Configuration error: The dev environment" in capsys.readouterr().err
