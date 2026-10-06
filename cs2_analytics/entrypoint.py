"""Console entry point for the `cs2a` command.

Configuration is read when the first project module is imported, which
happens before Typer parses any option. This module therefore resolves the
global `--env` option from the raw arguments, exports it as `CS2A_ENV`,
and only then imports the CLI. See ADR-0018.
"""

import os
import sys

import typer

from cs2_analytics.exceptions import ConfigurationError
from cs2_analytics.runtime_env import ENV_SELECTOR_VAR, RuntimeEnv

ENV_OPTION = "--env"
CONFIGURATION_ERROR_EXIT_CODE = 2


def requested_environment(argv: list[str]) -> str | None:
    """Returns the value given to `--env`, in either spelling, if present."""
    for index, argument in enumerate(argv):
        if argument == "--":
            return None
        if argument.startswith(f"{ENV_OPTION}="):
            return argument.split("=", 1)[1]
        if argument == ENV_OPTION and index + 1 < len(argv):
            return argv[index + 1]
    return None


def main() -> None:
    """Selects the environment, then hands the arguments to the Typer app."""
    requested = requested_environment(sys.argv[1:])
    # An unknown value is left for Typer to reject with its usage error.
    if requested in {env.value for env in RuntimeEnv}:
        os.environ[ENV_SELECTOR_VAR] = requested

    try:
        from cs2_analytics.cli import app
    except ConfigurationError as e:
        typer.echo(f"Configuration error: {e}", err=True)
        raise SystemExit(CONFIGURATION_ERROR_EXIT_CODE) from e

    app()
