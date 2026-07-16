"""Tests for the cs2a Typer CLI (issue #86).

The CLI wraps existing controllers, so these tests assert wiring: which
controller runs, with which arguments, in which order. Controllers are
replaced in their source modules because the CLI imports them lazily
inside command bodies.
"""

from typer.testing import CliRunner

from cs2_analytics.cli import app

runner = CliRunner()


class _RecordingController:
    """Controller stand-in appending (name, kwargs) to a shared call log."""

    def __init__(self, name: str, calls: list[tuple[str, dict]]) -> None:
        self._name = name
        self._calls = calls

    def run(self, **kwargs) -> None:
        self._calls.append((self._name, kwargs))


def _patch_controller(monkeypatch, module_path, class_name, name, calls):
    import importlib

    module = importlib.import_module(module_path)
    monkeypatch.setattr(module, class_name, lambda: _RecordingController(name, calls))


def _patch_alembic_command(monkeypatch, calls):
    """Replace alembic.command functions with recorders capturing revisions."""
    import alembic.command

    def _recorder(name):
        def _record(config, *args):
            calls.append((name, args))

        return _record

    for command_name in ("upgrade", "downgrade", "current"):
        monkeypatch.setattr(alembic.command, command_name, _recorder(command_name))


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("ingest", "process", "status", "db"):
        assert command in result.stdout


def test_discover_defaults_to_incremental_cap(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []
    _patch_controller(
        monkeypatch,
        "cs2_analytics.controllers.results_controller",
        "ResultsController",
        "results",
        calls,
    )

    result = runner.invoke(app, ["ingest", "discover"])

    assert result.exit_code == 0
    assert calls == [("results", {"max_matches": 50})]


def test_discover_backfill_raises_the_cap(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []
    _patch_controller(
        monkeypatch,
        "cs2_analytics.controllers.results_controller",
        "ResultsController",
        "results",
        calls,
    )

    result = runner.invoke(app, ["ingest", "discover", "--mode", "backfill"])

    assert result.exit_code == 0
    assert calls == [("results", {"max_matches": 1000})]


def test_discover_max_matches_overrides_mode(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []
    _patch_controller(
        monkeypatch,
        "cs2_analytics.controllers.results_controller",
        "ResultsController",
        "results",
        calls,
    )

    result = runner.invoke(
        app, ["ingest", "discover", "--mode", "backfill", "--max-matches", "7"]
    )

    assert result.exit_code == 0
    assert calls == [("results", {"max_matches": 7})]


def test_discover_rejects_nonpositive_max_matches(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []
    _patch_controller(
        monkeypatch,
        "cs2_analytics.controllers.results_controller",
        "ResultsController",
        "results",
        calls,
    )

    result = runner.invoke(app, ["ingest", "discover", "--max-matches", "0"])

    assert result.exit_code != 0
    assert calls == []


def test_process_rejects_nonpositive_batch(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []
    _patch_controller(
        monkeypatch,
        "cs2_analytics.controllers.match_controller",
        "MatchController",
        "match",
        calls,
    )

    result = runner.invoke(app, ["process", "--batch", "0"])

    assert result.exit_code != 0
    assert calls == []


def test_process_runs_matches_then_maps_with_batch(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []
    _patch_controller(
        monkeypatch,
        "cs2_analytics.controllers.match_controller",
        "MatchController",
        "match",
        calls,
    )
    _patch_controller(
        monkeypatch,
        "cs2_analytics.controllers.map_controller",
        "MapController",
        "map",
        calls,
    )

    result = runner.invoke(app, ["process", "--batch", "10"])

    assert result.exit_code == 0
    assert calls == [
        ("match", {"batch_size": 10}),
        ("map", {"batch_size": 10}),
    ]


def test_status_prints_counts_per_table(monkeypatch) -> None:
    import cs2_analytics.storage.ingestion_state_summary as summary_module

    monkeypatch.setattr(
        summary_module,
        "fetch_ingestion_state_counts",
        lambda: {
            "match_ingestion_state": {"processed": 3, "pending": 1},
            "map_ingestion_state": {},
            "demo_ingestion_state": {"failed": 2},
        },
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "match_ingestion_state:" in result.stdout
    assert "pending" in result.stdout
    assert "3" in result.stdout
    assert "(no rows)" in result.stdout
    assert "failed" in result.stdout


def test_status_exits_nonzero_when_database_is_unavailable(monkeypatch) -> None:
    import cs2_analytics.storage.ingestion_state_summary as summary_module
    from cs2_analytics.exceptions import DatabaseConnectionError

    def _raise():
        raise DatabaseConnectionError("no pool")

    monkeypatch.setattr(summary_module, "fetch_ingestion_state_counts", _raise)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1


def test_db_upgrade_defaults_to_head_and_prints_target(monkeypatch) -> None:
    calls: list[tuple[str, tuple]] = []
    _patch_alembic_command(monkeypatch, calls)

    result = runner.invoke(app, ["db", "upgrade"], input="y\n")

    assert result.exit_code == 0
    assert calls == [("upgrade", ("head",))]
    assert "Target database:" in result.stdout


def test_db_upgrade_accepts_explicit_revision(monkeypatch) -> None:
    calls: list[tuple[str, tuple]] = []
    _patch_alembic_command(monkeypatch, calls)

    result = runner.invoke(app, ["db", "upgrade", "20260521_0001"], input="y\n")

    assert result.exit_code == 0
    assert calls == [("upgrade", ("20260521_0001",))]


def test_db_upgrade_aborts_without_confirmation(monkeypatch) -> None:
    calls: list[tuple[str, tuple]] = []
    _patch_alembic_command(monkeypatch, calls)

    result = runner.invoke(app, ["db", "upgrade"], input="n\n")

    assert result.exit_code != 0
    assert calls == []
    assert "Target database:" in result.stdout


def test_db_downgrade_requires_a_revision(monkeypatch) -> None:
    calls: list[tuple[str, tuple]] = []
    _patch_alembic_command(monkeypatch, calls)

    result = runner.invoke(app, ["db", "downgrade"])

    assert result.exit_code != 0
    assert calls == []


def test_db_downgrade_aborts_without_confirmation(monkeypatch) -> None:
    calls: list[tuple[str, tuple]] = []
    _patch_alembic_command(monkeypatch, calls)

    result = runner.invoke(app, ["db", "downgrade", "20260521_0001"], input="n\n")

    assert result.exit_code != 0
    assert calls == []
    assert "Target database:" in result.stdout


def test_db_downgrade_runs_after_confirmation(monkeypatch) -> None:
    calls: list[tuple[str, tuple]] = []
    _patch_alembic_command(monkeypatch, calls)

    result = runner.invoke(app, ["db", "downgrade", "20260521_0001"], input="y\n")

    assert result.exit_code == 0
    assert calls == [("downgrade", ("20260521_0001",))]


def test_db_current_reports_revision_and_prints_target(monkeypatch) -> None:
    calls: list[tuple[str, tuple]] = []
    _patch_alembic_command(monkeypatch, calls)

    result = runner.invoke(app, ["db", "current"])

    assert result.exit_code == 0
    assert calls == [("current", ())]
    assert "Target database:" in result.stdout
