"""Tests for the cs2a Typer CLI (issue #86).

The CLI wraps existing controllers, so these tests assert wiring: which
controller runs, with which arguments, in which order. Controllers are
replaced in their source modules because the CLI imports them lazily
inside command bodies.
"""

import datetime as dt

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
    commands = ("ingest", "process", "retry", "failures", "inspect", "status", "db")
    for command in commands:
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
    assert calls == [("results", {"max_matches": 50, "start_date": dt.date(2025, 10, 1), "end_date": dt.date.today()})]


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
    assert calls == [("results", {"max_matches": 1000, "start_date": dt.date(2025, 10, 1), "end_date": dt.date.today()})]


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
    assert calls == [("results", {"max_matches": 7, "start_date": dt.date(2025, 10, 1), "end_date": dt.date.today()})]


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


def _patch_coverage(monkeypatch, report):
    """Replace the coverage fetch with a canned report in its module."""
    import cs2_analytics.storage.discovery_coverage as coverage_module

    calls: list[tuple] = []

    def _fetch(window_start, window_end, period):
        calls.append((window_start, window_end, period))
        return report

    monkeypatch.setattr(coverage_module, "fetch_discovery_coverage", _fetch)
    return calls


def test_ingest_coverage_reports_window_gaps_and_backlog(monkeypatch) -> None:
    import datetime as dt

    calls = _patch_coverage(
        monkeypatch,
        {
            "earliest_match": dt.datetime(2025, 10, 2, 12, 0),
            "latest_match": dt.datetime(2026, 8, 30, 20, 0),
            "total_matches": 700,
            "window_matches": 45,
            "period_counts": [(dt.date(2026, 8, 24), 45)],
            "pending_by_status": {"discovered": 561, "failed": 2},
        },
    )

    result = runner.invoke(app, ["ingest", "coverage"])

    assert result.exit_code == 0
    assert len(calls) == 1
    window_start, window_end, period = calls[0]
    assert window_start == dt.date(2025, 10, 1)
    assert window_end == dt.date.today()
    assert period == "week"
    assert "Discovery window: 2025-10-01" in result.stdout
    assert "(per week)" in result.stdout
    assert "Earliest match: 2025-10-02 12:00:00" in result.stdout
    assert "Matches in window: 45 (total in database: 700)" in result.stdout
    assert "Gaps (no matches, per week):" in result.stdout
    assert "Not yet processed (by status):" in result.stdout
    assert "discovered   561" in result.stdout
    assert "Note: gaps may reflect unprocessed backlog" in result.stdout


def test_ingest_coverage_day_period_and_quiet_when_no_backlog(monkeypatch) -> None:
    import datetime as dt

    today = dt.date.today()
    calls = _patch_coverage(
        monkeypatch,
        {
            "earliest_match": None,
            "latest_match": None,
            "total_matches": 0,
            "window_matches": 0,
            "period_counts": [(day, 1) for day in _all_days_since_start(today)],
            "pending_by_status": {},
        },
    )

    result = runner.invoke(app, ["ingest", "coverage", "--period", "day"])

    assert result.exit_code == 0
    assert calls[0][2] == "day"
    assert "Earliest match: -" in result.stdout
    assert "gap ranges: 0" in result.stdout
    assert "Gaps" not in result.stdout
    assert "Not yet processed" not in result.stdout
    assert "Note:" not in result.stdout


def _all_days_since_start(today):
    import datetime as dt

    start = dt.date(2025, 10, 1)
    return [start + dt.timedelta(days=i) for i in range((today - start).days + 1)]


def test_ingest_coverage_exits_nonzero_when_database_is_unavailable(
    monkeypatch,
) -> None:
    import cs2_analytics.storage.discovery_coverage as coverage_module
    from cs2_analytics.exceptions import DatabaseConnectionError

    def _raise(window_start, window_end, period):
        raise DatabaseConnectionError("no pool")

    monkeypatch.setattr(coverage_module, "fetch_discovery_coverage", _raise)

    result = runner.invoke(app, ["ingest", "coverage"])

    assert result.exit_code == 1
    assert "Database unavailable" in result.stderr


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


def _patch_failure_queries(monkeypatch, rows=None, groups=None):
    """Replace the failure query helpers with recorders in their module."""
    import cs2_analytics.storage.ingestion_state_summary as summary_module

    calls: list[tuple[str, tuple]] = []

    def _rows(stage, status, limit):
        calls.append(("rows", (stage, status, limit)))
        return rows or []

    def _groups(stage, status, limit):
        calls.append(("groups", (stage, status, limit)))
        return groups or []

    monkeypatch.setattr(summary_module, "fetch_failure_rows", _rows)
    monkeypatch.setattr(summary_module, "fetch_failure_groups", _groups)
    return calls


def test_failures_lists_rows_with_truncated_error(monkeypatch) -> None:
    long_error = "MatchParseError: " + "x" * 100
    calls = _patch_failure_queries(
        monkeypatch,
        rows=[
            (940123, "failed", 3, "2026-08-30 10:00:00+00:00", long_error),
            (940124, "failed", 1, None, None),
        ],
    )

    result = runner.invoke(app, ["failures", "--stage", "match"])

    assert result.exit_code == 0
    assert calls == [("rows", ("match", "failed", 20))]
    assert "940123" in result.stdout
    assert "failures=3" in result.stdout
    assert "2026-08-30 10:00:00+00:00" in result.stdout
    assert "..." in result.stdout
    assert long_error not in result.stdout
    assert "last_failed=-" in result.stdout
    assert "2 match row(s) in status 'failed'" in result.stdout


def test_failures_group_aggregates_by_error_message(monkeypatch) -> None:
    calls = _patch_failure_queries(
        monkeypatch,
        groups=[
            ("MapParseError: layout changed", 5, "2026-08-30 10:00:00+00:00"),
            (None, 1, None),
        ],
    )

    result = runner.invoke(
        app, ["failures", "--stage", "map", "--status", "dead", "--group"]
    )

    assert result.exit_code == 0
    assert calls == [("groups", ("map", "dead", 20))]
    assert "count=5" in result.stdout
    assert "MapParseError: layout changed" in result.stdout
    assert "(no error message)" in result.stdout
    assert (
        "2 failure group(s) in status 'dead' in map_ingestion_state" in result.stdout
    )


def test_failures_passes_status_and_limit_filters(monkeypatch) -> None:
    calls = _patch_failure_queries(monkeypatch)

    result = runner.invoke(
        app,
        ["failures", "--stage", "map", "--status", "partial", "--limit", "5"],
    )

    assert result.exit_code == 0
    assert calls == [("rows", ("map", "partial", 5))]
    assert "No partial rows in map_ingestion_state." in result.stdout


def test_failures_rejects_nonpositive_limit(monkeypatch) -> None:
    calls = _patch_failure_queries(monkeypatch)

    result = runner.invoke(app, ["failures", "--stage", "match", "--limit", "0"])

    assert result.exit_code != 0
    assert calls == []


def test_failures_rejects_processing_status(monkeypatch) -> None:
    calls = _patch_failure_queries(monkeypatch)

    result = runner.invoke(
        app, ["failures", "--stage", "match", "--status", "processing"]
    )

    assert result.exit_code != 0
    assert calls == []


def test_failures_exits_nonzero_when_database_is_unavailable(monkeypatch) -> None:
    import cs2_analytics.storage.ingestion_state_summary as summary_module
    from cs2_analytics.exceptions import DatabaseConnectionError

    def _raise(stage, status, limit):
        raise DatabaseConnectionError("no pool")

    monkeypatch.setattr(summary_module, "fetch_failure_rows", _raise)

    result = runner.invoke(app, ["failures", "--stage", "match"])

    assert result.exit_code == 1
    assert "Database unavailable" in result.stderr


def _patch_inspections(monkeypatch, match_result=None, map_result=None):
    """Replace the inspection helpers with canned results in their module."""
    import cs2_analytics.storage.ingestion_state_summary as summary_module

    calls: list[tuple[str, int]] = []

    def _match(match_id):
        calls.append(("match", match_id))
        return match_result

    def _map(map_id):
        calls.append(("map", map_id))
        return map_result

    monkeypatch.setattr(summary_module, "fetch_match_inspection", _match)
    monkeypatch.setattr(summary_module, "fetch_map_inspection", _map)
    return calls


def test_inspect_match_shows_state_and_relational_presence(monkeypatch) -> None:
    calls = _patch_inspections(
        monkeypatch,
        match_result={
            "state": {
                "match_id": 101,
                "status": "processed",
                "failure_count": 0,
                "last_error_message": None,
            },
            "match_row_exists": True,
            "map_rows": 3,
            "map_states": [(201, "processed"), (202, "failed")],
        },
    )

    result = runner.invoke(app, ["inspect", "match", "101"])

    assert result.exit_code == 0
    assert calls == [("match", 101)]
    assert "match_ingestion_state:" in result.stdout
    assert "processed" in result.stdout
    assert "last_error_message" in result.stdout
    assert "-" in result.stdout
    assert "matches row: present" in result.stdout
    assert "maps rows: 3" in result.stdout
    assert "202  failed" in result.stdout


def test_inspect_match_unknown_id_exits_nonzero(monkeypatch) -> None:
    _patch_inspections(
        monkeypatch,
        match_result={
            "state": None,
            "match_row_exists": False,
            "map_rows": 0,
            "map_states": [],
        },
    )

    result = runner.invoke(app, ["inspect", "match", "999"])

    assert result.exit_code == 1
    assert "No match_ingestion_state row for match 999." in result.stdout
    assert "Match 999 not found." in result.stderr


def test_inspect_match_without_state_row_still_reports_relational(
    monkeypatch,
) -> None:
    _patch_inspections(
        monkeypatch,
        match_result={
            "state": None,
            "match_row_exists": True,
            "map_rows": 2,
            "map_states": [],
        },
    )

    result = runner.invoke(app, ["inspect", "match", "101"])

    assert result.exit_code == 0
    assert "No match_ingestion_state row for match 101." in result.stdout
    assert "matches row: present" in result.stdout
    assert "maps rows: 2" in result.stdout


def test_inspect_map_shows_state_and_player_count(monkeypatch) -> None:
    calls = _patch_inspections(
        monkeypatch,
        map_result={
            "state": {"map_id": 230075, "status": "failed", "failure_count": 2},
            "map_row_exists": False,
            "player_rows": 0,
        },
    )

    result = runner.invoke(app, ["inspect", "map", "230075"])

    assert result.exit_code == 0
    assert calls == [("map", 230075)]
    assert "map_ingestion_state:" in result.stdout
    assert "maps row: MISSING" in result.stdout
    assert "players rows: 0" in result.stdout


def test_inspect_map_unknown_id_exits_nonzero(monkeypatch) -> None:
    _patch_inspections(
        monkeypatch,
        map_result={"state": None, "map_row_exists": False, "player_rows": 0},
    )

    result = runner.invoke(app, ["inspect", "map", "999"])

    assert result.exit_code == 1
    assert "Map 999 not found." in result.stderr


def test_inspect_exits_nonzero_when_database_is_unavailable(monkeypatch) -> None:
    import cs2_analytics.storage.ingestion_state_summary as summary_module
    from cs2_analytics.exceptions import DatabaseConnectionError

    def _raise(item_id):
        raise DatabaseConnectionError("no pool")

    monkeypatch.setattr(summary_module, "fetch_match_inspection", _raise)

    result = runner.invoke(app, ["inspect", "match", "101"])

    assert result.exit_code == 1
    assert "Database unavailable" in result.stderr


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


def test_retry_processing_requires_explicit_status_and_warns(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(7, 0, None)], calls)

    result = runner.invoke(
        app, ["retry", "--stage", "map", "--status", "processing"], input="y\n"
    )

    assert result.exit_code == 0
    assert "duplicate processing" in result.stdout
    assert calls == [
        ("fetch", "map", {"status": "processing", "limit": None, "id": None}),
        ("requeue", "map", {"ids": [7], "expected_status": "processing"}),
    ]


def test_retry_processing_dry_run_previews_without_writing(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(7, 0, None), (8, 2, "boom")], calls)

    result = runner.invoke(
        app, ["retry", "--stage", "match", "--status", "processing", "--dry-run"]
    )

    assert result.exit_code == 0
    assert [call[0] for call in calls] == ["fetch"]
    assert "duplicate processing" in result.stdout
    assert "2 match row(s) in status 'processing'" in result.stdout
    assert "Dry run: no rows were changed." in result.stdout


def test_retry_never_touches_processing_unless_named(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []
    _patch_retry_states(monkeypatch, [(1, 3, "boom")], calls)

    result = runner.invoke(app, ["retry", "--stage", "match", "--id", "1"], input="y\n")

    assert result.exit_code == 0
    assert all(call[2].get("status", call[2].get("expected_status")) == "failed" for call in calls)
    assert "duplicate processing" not in result.stdout
