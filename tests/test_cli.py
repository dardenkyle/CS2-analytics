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
        def _record(config, *args, **kwargs):
            calls.append((name, args))

        return _record

    for command_name in ("upgrade", "downgrade", "current"):
        monkeypatch.setattr(alembic.command, command_name, _recorder(command_name))


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("ingest", "process", "retry", "status", "db"):
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


class _FakeRetryState:
    """Ingestion-state stand-in recording fetch/requeue calls per stage."""

    def __init__(
        self,
        name: str,
        table_name: str,
        candidates: list[tuple],
        calls: list[tuple[str, str, dict]],
        requeue_result: int | None = None,
    ) -> None:
        self.table_name = table_name
        self._name = name
        self._candidates = candidates
        self._calls = calls
        self._requeue_result = requeue_result

    def fetch_requeue_candidates(self, status, limit=None, id_value=None):
        self._calls.append(
            ("fetch", self._name, {"status": status, "limit": limit, "id": id_value})
        )
        return self._candidates

    def requeue(self, ids, expected_status):
        self._calls.append(
            ("requeue", self._name, {"ids": ids, "expected_status": expected_status})
        )
        if self._requeue_result is not None:
            return self._requeue_result
        return len(ids)


def _patch_retry_states(monkeypatch, candidates, calls, requeue_result=None):
    """Replace both lazily imported state classes with recording fakes."""
    import importlib

    match_module = importlib.import_module(
        "cs2_analytics.ingestion_state.match_ingestion_state"
    )
    map_module = importlib.import_module(
        "cs2_analytics.ingestion_state.map_ingestion_state"
    )

    monkeypatch.setattr(
        match_module,
        "MatchIngestionState",
        lambda: _FakeRetryState(
            "match", "match_ingestion_state", candidates, calls, requeue_result
        ),
    )
    monkeypatch.setattr(
        map_module,
        "MapIngestionState",
        lambda: _FakeRetryState(
            "map", "map_ingestion_state", candidates, calls, requeue_result
        ),
    )


def test_retry_requires_a_stage(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(1, 3, "boom")], calls)

    result = runner.invoke(app, ["retry"])

    assert result.exit_code != 0
    assert calls == []


def test_retry_defaults_to_failed_and_requeues_after_confirmation(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(1, 3, "boom"), (2, 1, None)], calls)

    result = runner.invoke(app, ["retry", "--stage", "match"], input="y\n")

    assert result.exit_code == 0
    assert calls == [
        ("fetch", "match", {"status": "failed", "limit": None, "id": None}),
        ("requeue", "match", {"ids": [1, 2], "expected_status": "failed"}),
    ]
    assert "2 match row(s) in status 'failed'" in result.stdout
    assert "Target database:" in result.stdout
    assert "Requeued 2 row(s)" in result.stdout


def test_retry_map_stage_uses_map_state(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(7, 2, "boom")], calls)

    result = runner.invoke(app, ["retry", "--stage", "map"], input="y\n")

    assert result.exit_code == 0
    assert [call[1] for call in calls] == ["map", "map"]


def test_retry_dead_and_partial_require_explicit_status(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(1, 5, "gone")], calls)

    result = runner.invoke(
        app, ["retry", "--stage", "match", "--status", "dead"], input="y\n"
    )

    assert result.exit_code == 0
    assert calls == [
        ("fetch", "match", {"status": "dead", "limit": None, "id": None}),
        ("requeue", "match", {"ids": [1], "expected_status": "dead"}),
    ]


def test_retry_passes_limit_and_id_filters(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(42, 1, "boom")], calls)

    result = runner.invoke(
        app,
        ["retry", "--stage", "match", "--limit", "5", "--id", "42"],
        input="y\n",
    )

    assert result.exit_code == 0
    assert calls[0] == ("fetch", "match", {"status": "failed", "limit": 5, "id": 42})


def test_retry_dry_run_reports_rows_without_writing(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(1, 3, "boom")], calls)

    result = runner.invoke(app, ["retry", "--stage", "match", "--dry-run"])

    assert result.exit_code == 0
    assert [call[0] for call in calls] == ["fetch"]
    assert "Dry run: no rows were changed." in result.stdout
    assert "1 match row(s) in status 'failed'" in result.stdout


def test_retry_truncates_long_error_previews(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    long_error = "x" * 100
    _patch_retry_states(monkeypatch, [(1, 2, long_error)], calls)

    result = runner.invoke(app, ["retry", "--stage", "match", "--dry-run"])

    assert result.exit_code == 0
    assert "x" * 60 + "..." in result.stdout
    assert "x" * 61 not in result.stdout


def test_retry_reports_rows_left_alone_when_status_changed(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(
        monkeypatch, [(1, 3, "boom"), (2, 1, None)], calls, requeue_result=1
    )

    result = runner.invoke(app, ["retry", "--stage", "match"], input="y\n")

    assert result.exit_code == 0
    assert "Requeued 1 row(s)" in result.stdout
    assert (
        "1 row(s) changed status since the preview and were left alone."
        in result.stdout
    )


def test_retry_aborts_without_confirmation(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(1, 3, "boom")], calls)

    result = runner.invoke(app, ["retry", "--stage", "match"], input="n\n")

    assert result.exit_code != 0
    assert [call[0] for call in calls] == ["fetch"]
    assert "Target database:" in result.stdout


def test_retry_reports_when_nothing_matches(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [], calls)

    result = runner.invoke(app, ["retry", "--stage", "match"])

    assert result.exit_code == 0
    assert [call[0] for call in calls] == ["fetch"]
    assert "No failed rows to requeue in match_ingestion_state." in result.stdout


def test_retry_exits_nonzero_when_fetch_fails(monkeypatch) -> None:
    import importlib

    from cs2_analytics.exceptions import MatchIngestionStateError

    match_module = importlib.import_module(
        "cs2_analytics.ingestion_state.match_ingestion_state"
    )

    class _FailingState:
        def fetch_requeue_candidates(self, status, limit=None, id_value=None):
            raise MatchIngestionStateError("db down")

    monkeypatch.setattr(match_module, "MatchIngestionState", lambda: _FailingState())

    result = runner.invoke(app, ["retry", "--stage", "match"])

    assert result.exit_code == 1


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
