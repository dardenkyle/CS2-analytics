"""Typer CLI exposing the ingestion pipeline as the `cs2a` command.

Registered as the `cs2a` console script in pyproject.toml. Commands wrap
the existing controllers without changing their behavior. Controller
imports live inside the command bodies so `cs2a --help` and `cs2a status`
do not pay the scraper-stack import cost.
"""

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


class DiscoverMode(StrEnum):
    """Depth of a results-discovery pass."""

    INCREMENTAL = "incremental"
    BACKFILL = "backfill"


DISCOVER_MODE_MAX_MATCHES = {
    DiscoverMode.INCREMENTAL: 50,
    DiscoverMode.BACKFILL: 1000,
}


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
    ResultsController().run(max_matches=cap)


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


class RetryStage(StrEnum):
    """Ingestion stage whose state table a requeue targets."""

    MATCH = "match"
    MAP = "map"


class RetryStatus(StrEnum):
    """Lifecycle statuses eligible for requeueing."""

    FAILED = "failed"
    DEAD = "dead"
    PARTIAL = "partial"


RETRY_ERROR_PREVIEW_LENGTH = 60


def _retry_state_for(stage: RetryStage) -> "BaseIngestionState[int]":
    """Return the ingestion-state manager for the requested retry stage."""
    from cs2_analytics.ingestion_state.map_ingestion_state import MapIngestionState
    from cs2_analytics.ingestion_state.match_ingestion_state import MatchIngestionState

    if stage is RetryStage.MATCH:
        return MatchIngestionState()
    return MapIngestionState()


@app.command()
def retry(
    stage: Annotated[
        RetryStage,
        typer.Option(help="Ingestion stage whose state rows to requeue."),
    ],
    status: Annotated[
        RetryStatus,
        typer.Option(
            help=(
                "Status to requeue. dead and partial rows are only requeued "
                "when named here explicitly, including with --id."
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
    run picks the requeued rows up.
    """
    state = _retry_state_for(stage)
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
        error_preview = last_error or ""
        if len(error_preview) > RETRY_ERROR_PREVIEW_LENGTH:
            error_preview = error_preview[:RETRY_ERROR_PREVIEW_LENGTH] + "..."
        typer.echo(f"  {row_id}  failures={failure_count or 0}  {error_preview}")
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
