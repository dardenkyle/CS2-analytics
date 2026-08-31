"""Typer CLI exposing the ingestion pipeline as the `cs2a` command.

Registered as the `cs2a` console script in pyproject.toml. Commands wrap
the existing controllers without changing their behavior. Controller
imports live inside the command bodies so `cs2a --help` and `cs2a status`
do not pay the scraper-stack import cost.
"""

import datetime as dt
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated

import typer

from cs2_analytics.exceptions import DatabaseConnectionError, IngestionStateError

if TYPE_CHECKING:
    from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState

app = typer.Typer(
    help="CS2 analytics ingestion pipeline.",
    no_args_is_help=True,
)
ingest_app = typer.Typer(
    help="Discovery commands that queue new ingestion work.",
    no_args_is_help=True,
)
app.add_typer(ingest_app, name="ingest")
db_app = typer.Typer(
    help="Schema migration commands wrapping Alembic.",
    no_args_is_help=True,
)
app.add_typer(db_app, name="db")
inspect_app = typer.Typer(
    help="Read-only per-item ingestion diagnostics.",
    no_args_is_help=True,
)
app.add_typer(inspect_app, name="inspect")


class DiscoverMode(StrEnum):
    """Depth of a results-discovery pass."""

    INCREMENTAL = "incremental"
    BACKFILL = "backfill"


DISCOVER_MODE_MAX_MATCHES = {
    DiscoverMode.INCREMENTAL: 50,
    DiscoverMode.BACKFILL: 1000,
}

# Discovery window floor. Run parameters live with the invoker, not in
# config (ADR-0015); the pipeline imports these same defaults so both
# entry points stay aligned. The end of the window is always computed at
# run time. #121 turns the floor into a real backfill cursor target.
DISCOVERY_WINDOW_START = dt.date(2025, 10, 1)


@ingest_app.command("discover")
def discover(
    mode: Annotated[
        DiscoverMode,
        typer.Option(help="incremental caps at 50 matches; backfill at 1000."),
    ] = DiscoverMode.INCREMENTAL,
    max_matches: Annotated[
        int | None,
        typer.Option(min=1, help="Override the per-mode match cap."),
    ] = None,
) -> None:
    """Scrape results pages and queue newly discovered matches."""
    from cs2_analytics.controllers.results_controller import ResultsController

    cap = max_matches if max_matches is not None else DISCOVER_MODE_MAX_MATCHES[mode]
    ResultsController().run(
        max_matches=cap,
        start_date=DISCOVERY_WINDOW_START,
        end_date=dt.date.today(),
    )


class CoveragePeriod(StrEnum):
    """Bucket size for the discovery-coverage report."""

    DAY = "day"
    WEEK = "week"


@ingest_app.command("coverage")
def coverage(
    period: Annotated[
        CoveragePeriod,
        typer.Option(help="Bucket size for per-period counts and gaps."),
    ] = CoveragePeriod.WEEK,
) -> None:
    """Report discovery date coverage of the target window.

    Read-only: compares the discovery window (DISCOVERY_WINDOW_START
    through today) against match dates present in `matches`, lists
    zero-match periods as gaps, and shows the not-yet-processed backlog
    (every non-processed lifecycle status) so "not discovered" is
    distinguishable from "not yet processed". Backfill cursor state
    joins this report once the backfill strategy (#121) lands.
    """
    from cs2_analytics.storage.discovery_coverage import (
        compute_gap_ranges,
        fetch_discovery_coverage,
    )

    window_start = DISCOVERY_WINDOW_START
    window_end = dt.date.today()
    try:
        report = fetch_discovery_coverage(window_start, window_end, period.value)
    except DatabaseConnectionError as e:
        typer.echo(f"Database unavailable: {e}", err=True)
        raise typer.Exit(code=1) from e

    gaps = compute_gap_ranges(
        window_start, window_end, period.value, report["period_counts"]
    )
    typer.echo(
        f"Discovery window: {window_start} .. {window_end} (per {period.value})"
    )
    typer.echo(f"Earliest match: {report['earliest_match'] or '-'}")
    typer.echo(f"Latest match:   {report['latest_match'] or '-'}")
    typer.echo(
        f"Matches in window: {report['window_matches']}"
        f" (total in database: {report['total_matches']})"
    )
    covered = len(report["period_counts"])
    typer.echo(f"Covered periods: {covered}; gap ranges: {len(gaps)}")
    if gaps:
        typer.echo(f"Gaps (no matches, per {period.value}):")
        for gap_start, gap_end in gaps:
            typer.echo(f"  {gap_start} .. {gap_end}")
    pending = report["pending_by_status"]
    if pending:
        typer.echo("Not yet processed (by status):")
        for status_name, row_count in pending.items():
            typer.echo(f"  {status_name:<12} {row_count}")
        typer.echo(
            "Note: gaps may reflect unprocessed backlog rather than"
            " undiscovered dates."
        )


@app.command()
def process(
    batch: Annotated[
        int,
        typer.Option(min=1, help="Items to process per stage batch."),
    ] = 50,
) -> None:
    """Process pending matches, then pending maps."""
    from cs2_analytics.controllers.map_controller import MapController
    from cs2_analytics.controllers.match_controller import MatchController

    MatchController().run(batch_size=batch)
    MapController().run(batch_size=batch)


class IngestionStage(StrEnum):
    """Ingestion stage whose state table a command targets."""

    MATCH = "match"
    MAP = "map"


class RetryStatus(StrEnum):
    """Lifecycle statuses eligible for requeueing."""

    FAILED = "failed"
    DEAD = "dead"
    PARTIAL = "partial"
    PROCESSING = "processing"


class FailureStatus(StrEnum):
    """Lifecycle statuses carrying failure diagnostics."""

    FAILED = "failed"
    DEAD = "dead"
    PARTIAL = "partial"


PROCESSING_RELEASE_WARNING = (
    "Warning: releasing 'processing' rows while a pipeline run is active can "
    "cause duplicate processing. Confirm no run is in flight before continuing."
)


ERROR_PREVIEW_LENGTH = 60


def _error_preview(message: str | None) -> str:
    """Truncate an error message for single-line terminal listings."""
    preview = message or ""
    if len(preview) > ERROR_PREVIEW_LENGTH:
        preview = preview[:ERROR_PREVIEW_LENGTH] + "..."
    return preview


def _retry_state_for(stage: IngestionStage) -> "BaseIngestionState[int]":
    """Return the ingestion-state manager for the requested retry stage."""
    from cs2_analytics.ingestion_state.map_ingestion_state import MapIngestionState
    from cs2_analytics.ingestion_state.match_ingestion_state import MatchIngestionState

    if stage is IngestionStage.MATCH:
        return MatchIngestionState()
    return MapIngestionState()


@app.command()
def retry(
    stage: Annotated[
        IngestionStage,
        typer.Option(help="Ingestion stage whose state rows to requeue."),
    ],
    status: Annotated[
        RetryStatus,
        typer.Option(
            help=(
                "Status to requeue. dead, partial, and processing rows are only "
                "requeued when named here explicitly, including with --id. "
                "processing releases rows orphaned by an interrupted run."
            ),
        ),
    ] = RetryStatus.FAILED,
    limit: Annotated[
        int | None,
        typer.Option(min=1, help="Requeue at most this many rows."),
    ] = None,
    item_id: Annotated[
        int | None,
        typer.Option("--id", help="Requeue a single match/map by ID."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print what would be requeued without writing."),
    ] = False,
) -> None:
    """Requeue failed ingestion work by resetting rows to 'discovered'.

    failure_count and last_error_message are preserved as history; the
    requeue itself is visible via last_updated_at. The next `cs2a process`
    run picks the requeued rows up. --status processing releases rows
    orphaned in 'processing' by an interrupted run (#142); the operator is
    responsible for confirming no run is currently in flight.
    """
    state = _retry_state_for(stage)
    if status is RetryStatus.PROCESSING:
        typer.echo(PROCESSING_RELEASE_WARNING)
    try:
        candidates = state.fetch_requeue_candidates(
            status.value, limit=limit, id_value=item_id
        )
    except IngestionStateError as e:
        typer.echo(f"Failed to fetch requeue candidates: {e}", err=True)
        raise typer.Exit(code=1) from e

    if not candidates:
        typer.echo(f"No {status.value} rows to requeue in {state.table_name}.")
        return

    for row_id, failure_count, last_error in candidates:
        typer.echo(
            f"  {row_id}  failures={failure_count or 0}  {_error_preview(last_error)}"
        )
    typer.echo(f"{len(candidates)} {stage.value} row(s) in status '{status.value}'.")

    if dry_run:
        typer.echo("Dry run: no rows were changed.")
        return

    _echo_target_database()
    typer.confirm(f"Requeue {len(candidates)} row(s) to 'discovered'?", abort=True)
    try:
        requeued = state.requeue([row[0] for row in candidates], status.value)
    except IngestionStateError as e:
        typer.echo(f"Failed to requeue rows: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(f"Requeued {requeued} row(s); failure_count preserved as history.")
    skipped = len(candidates) - requeued
    if skipped > 0:
        typer.echo(
            f"{skipped} row(s) changed status since the preview and were left alone."
        )


@app.command()
def failures(
    stage: Annotated[
        IngestionStage,
        typer.Option(help="Ingestion stage whose failure rows to show."),
    ],
    status: Annotated[
        FailureStatus,
        typer.Option(help="Lifecycle status to inspect."),
    ] = FailureStatus.FAILED,
    limit: Annotated[
        int,
        typer.Option(min=1, help="Show at most this many rows or groups."),
    ] = 20,
    group: Annotated[
        bool,
        typer.Option(
            "--group",
            help="Aggregate rows by error message instead of listing them.",
        ),
    ] = False,
) -> None:
    """Show recent ingestion failures with their stored error details.

    Read-only: surfaces failure_count, last_failed_at, and a truncated
    last_error_message so the operator can tell transient scraper noise
    from a structural break before requeueing anything with `cs2a retry`.
    """
    from cs2_analytics.storage.ingestion_state_summary import (
        FAILURE_STAGE_TABLES,
        fetch_failure_groups,
        fetch_failure_rows,
    )

    table, _ = FAILURE_STAGE_TABLES[stage.value]
    try:
        if group:
            groups = fetch_failure_groups(stage.value, status.value, limit)
        else:
            rows = fetch_failure_rows(stage.value, status.value, limit)
    except DatabaseConnectionError as e:
        typer.echo(f"Database unavailable: {e}", err=True)
        raise typer.Exit(code=1) from e

    if group:
        if not groups:
            typer.echo(f"No {status.value} rows in {table}.")
            return
        for message, row_count, latest_failed_at in groups:
            typer.echo(
                f"  count={row_count}  latest={latest_failed_at or '-'}"
                f"  {_error_preview(message) or '(no error message)'}"
            )
        typer.echo(
            f"{len(groups)} failure group(s) in status '{status.value}' in {table}."
        )
        return

    if not rows:
        typer.echo(f"No {status.value} rows in {table}.")
        return
    for row_id, row_status, failure_count, last_failed_at, message in rows:
        typer.echo(
            f"  {row_id}  {row_status}  failures={failure_count or 0}"
            f"  last_failed={last_failed_at or '-'}  {_error_preview(message)}"
        )
    typer.echo(f"{len(rows)} {stage.value} row(s) in status '{status.value}'.")


def _echo_state_row(table: str, state: dict[str, object]) -> None:
    """Print one ingestion-state row as aligned name/value lines."""
    typer.echo(f"{table}:")
    for name, value in state.items():
        typer.echo(f"  {name:<20} {'-' if value is None else value}")


@inspect_app.command("match")
def inspect_match(
    match_id: Annotated[
        int,
        typer.Argument(help="Match ID to inspect."),
    ],
) -> None:
    """Show one match's ingestion-state row and relational presence.

    Answers "this match says processed - is its data actually there?":
    the full match_ingestion_state row, whether the matches row exists,
    how many maps rows reference it, and each map's ingestion status.
    """
    from cs2_analytics.storage.ingestion_state_summary import fetch_match_inspection

    try:
        inspection = fetch_match_inspection(match_id)
    except DatabaseConnectionError as e:
        typer.echo(f"Database unavailable: {e}", err=True)
        raise typer.Exit(code=1) from e

    state = inspection["state"]
    if state is None:
        typer.echo(f"No match_ingestion_state row for match {match_id}.")
        if not inspection["match_row_exists"]:
            typer.echo(f"Match {match_id} not found.", err=True)
            raise typer.Exit(code=1)
    else:
        _echo_state_row("match_ingestion_state", state)
    typer.echo(
        f"matches row: {'present' if inspection['match_row_exists'] else 'MISSING'}"
    )
    typer.echo(f"maps rows: {inspection['map_rows']}")
    map_states = inspection["map_states"]
    if map_states:
        typer.echo("map ingestion statuses:")
        for map_id, map_status in map_states:
            typer.echo(f"  {map_id}  {map_status}")


@inspect_app.command("map")
def inspect_map(
    map_id: Annotated[
        int,
        typer.Argument(help="Map ID to inspect."),
    ],
) -> None:
    """Show one map's ingestion-state row and relational presence.

    The full map_ingestion_state row, whether the maps row exists, and
    how many player-stats rows the map has.
    """
    from cs2_analytics.storage.ingestion_state_summary import fetch_map_inspection

    try:
        inspection = fetch_map_inspection(map_id)
    except DatabaseConnectionError as e:
        typer.echo(f"Database unavailable: {e}", err=True)
        raise typer.Exit(code=1) from e

    state = inspection["state"]
    if state is None:
        typer.echo(f"No map_ingestion_state row for map {map_id}.")
        if not inspection["map_row_exists"]:
            typer.echo(f"Map {map_id} not found.", err=True)
            raise typer.Exit(code=1)
    else:
        _echo_state_row("map_ingestion_state", state)
    typer.echo(
        f"maps row: {'present' if inspection['map_row_exists'] else 'MISSING'}"
    )
    typer.echo(f"players rows: {inspection['player_rows']}")


def _alembic_config():
    """Load the project's Alembic configuration for programmatic commands.

    alembic.ini declares script_location and prepend_sys_path relative to
    the repository root, so both are overridden with absolute paths (as
    initialize_db.run_migrations does) to keep `cs2a db` working from any
    working directory.
    """
    from pathlib import Path

    from alembic.config import Config

    package_root = Path(__file__).resolve().parent
    config = Config(str(package_root / "alembic.ini"))
    config.set_main_option("script_location", str(package_root / "alembic"))
    config.set_main_option("prepend_sys_path", str(package_root.parent))
    return config


def _echo_target_database() -> None:
    """Print the target database so the operator sees local versus production."""
    from cs2_analytics.config.config import DB_HOST, DB_NAME, DB_PORT

    typer.echo(f"Target database: {DB_NAME} on {DB_HOST}:{DB_PORT}")


@db_app.command("upgrade")
def db_upgrade(
    revision: Annotated[
        str,
        typer.Argument(help="Target revision to migrate up to."),
    ] = "head",
) -> None:
    """Apply schema migrations up to the given revision, after confirming."""
    from alembic import command

    _echo_target_database()
    typer.confirm(f"Upgrade the database to revision '{revision}'?", abort=True)
    command.upgrade(_alembic_config(), revision)


@db_app.command("downgrade")
def db_downgrade(
    revision: Annotated[
        str,
        typer.Argument(help="Revision to revert the schema down to."),
    ],
) -> None:
    """Revert schema migrations down to the given revision, after confirming."""
    from alembic import command

    _echo_target_database()
    typer.confirm(f"Downgrade the database to revision '{revision}'?", abort=True)
    command.downgrade(_alembic_config(), revision)


@db_app.command("current")
def db_current() -> None:
    """Show the revision the database is currently at."""
    from alembic import command

    _echo_target_database()
    command.current(_alembic_config())


@app.command()
def status() -> None:
    """Print ingestion-state row counts grouped by lifecycle status."""
    from cs2_analytics.storage.ingestion_state_summary import (
        fetch_ingestion_state_counts,
    )

    try:
        counts = fetch_ingestion_state_counts()
    except DatabaseConnectionError as e:
        typer.echo(f"Database unavailable: {e}", err=True)
        raise typer.Exit(code=1) from e

    for table, statuses in counts.items():
        typer.echo(f"{table}:")
        if not statuses:
            typer.echo("  (no rows)")
        for state_name, row_count in sorted(statuses.items()):
            typer.echo(f"  {state_name:<12} {row_count}")
