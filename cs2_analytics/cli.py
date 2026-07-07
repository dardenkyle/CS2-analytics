"""Typer CLI exposing the ingestion pipeline as the `cs2a` command.

Registered as the `cs2a` console script in pyproject.toml. Commands wrap
the existing controllers without changing their behavior. Controller
imports live inside the command bodies so `cs2a --help` and `cs2a status`
do not pay the scraper-stack import cost.
"""

from enum import StrEnum
from typing import Annotated

import typer

from cs2_analytics.exceptions import DatabaseConnectionError

app = typer.Typer(
    help="CS2 analytics ingestion pipeline.",
    no_args_is_help=True,
)
ingest_app = typer.Typer(
    help="Discovery commands that queue new ingestion work.",
    no_args_is_help=True,
)
app.add_typer(ingest_app, name="ingest")


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
        typer.Option(help="Override the per-mode match cap."),
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
        typer.Option(help="Items to process per stage batch."),
    ] = 50,
) -> None:
    """Process pending matches, then pending maps."""
    from cs2_analytics.controllers.map_controller import MapController
    from cs2_analytics.controllers.match_controller import MatchController

    MatchController().run(batch_size=batch)
    MapController().run(batch_size=batch)


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
