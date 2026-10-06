"""Selects which env file configures the process.

Three named environments map to env files at the project root: `dev`
reads `.env.dev` and is the default, `test` reads `.env.test`, and `prod`
reads `.env.prod`. The selection comes from the `CS2A_ENV`
variable, which `cs2a --env` sets before any project module loads. The
selected file is loaded over the process environment, so a stale shell
export cannot repoint a command at another database, and `dev` and `test`
refuse a non-local database host. See ADR-0018.

This module must not import the config package: the `cs2a` entry point
imports it to resolve `--env` before configuration is read.
"""

import os
from enum import StrEnum
from pathlib import Path

from dotenv import load_dotenv

from cs2_analytics.exceptions import ConfigurationError

ENV_SELECTOR_VAR = "CS2A_ENV"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimeEnv(StrEnum):
    """Named environment a process runs against."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


ENV_FILES = {
    RuntimeEnv.DEV: ".env.dev",
    RuntimeEnv.TEST: ".env.test",
    RuntimeEnv.PROD: ".env.prod",
}

# The single file every command read before environments were named. It is
# never loaded now; finding one means a checkout has not been migrated.
LEGACY_ENV_FILE = ".env"

# Set by the first load_selected_environment() call. The file is read once
# per process so a later reload of the config module does not re-apply it
# over values changed since.
_active: RuntimeEnv | None = None


def env_file_path(env: RuntimeEnv) -> Path:
    """Returns where the env file for an environment lives."""
    return PROJECT_ROOT / ENV_FILES[env]


def _explicit_selection() -> RuntimeEnv | None:
    """Reads CS2A_ENV, rejecting a value that names no environment."""
    raw_value = os.environ.get(ENV_SELECTOR_VAR, "").strip().lower()
    if not raw_value:
        return None
    try:
        return RuntimeEnv(raw_value)
    except ValueError as exc:
        choices = ", ".join(env.value for env in RuntimeEnv)
        raise ConfigurationError(
            f"{ENV_SELECTOR_VAR} must be one of: {choices}."
        ) from exc


def _is_deployed_runtime() -> bool:
    """True for a runtime with no local env file that declares production.

    Containers and hosted services receive real environment variables and
    ship no env file, so `ENVIRONMENT=production` there is the explicit
    selection. A machine with a `.env.dev` file never takes this path.
    """
    declared = os.environ.get("ENVIRONMENT", "").strip().lower()
    return declared == "production" and not env_file_path(RuntimeEnv.DEV).is_file()


def resolve_environment() -> RuntimeEnv:
    """Returns the selected environment: explicit, deployed, or `dev`."""
    explicit = _explicit_selection()
    if explicit is not None:
        return explicit
    if _is_deployed_runtime():
        return RuntimeEnv.PROD
    return RuntimeEnv.DEV


def _refuse_legacy_env_file() -> None:
    """Stops instead of silently ignoring a leftover unnamed `.env` file."""
    if not (PROJECT_ROOT / LEGACY_ENV_FILE).is_file():
        return
    raise ConfigurationError(
        f"{LEGACY_ENV_FILE} in {PROJECT_ROOT} is no longer read. Rename it to "
        f"{ENV_FILES[RuntimeEnv.DEV]} if it points at a local database, or to "
        f"{ENV_FILES[RuntimeEnv.PROD]} if it holds deployed credentials."
    )


def load_selected_environment() -> RuntimeEnv:
    """Loads the selected env file over the process environment, once.

    An explicitly selected `test` or `prod` environment must have its file;
    `dev` may run on defaults, and a deployed runtime has no file at all.
    """
    global _active

    if _active is not None:
        return _active

    _refuse_legacy_env_file()
    selected = resolve_environment()
    env_file = env_file_path(selected)
    if env_file.is_file():
        load_dotenv(env_file, override=True)
    elif selected is not RuntimeEnv.DEV and _explicit_selection() is not None:
        raise ConfigurationError(
            f"The {selected.value} environment was selected but {env_file.name} "
            f"does not exist in {PROJECT_ROOT}."
        )
    _active = selected
    return selected


def refuse_non_local_host(
    active: RuntimeEnv, db_host: str, local_hosts: frozenset[str]
) -> None:
    """Stops `dev` and `test` from running against a deployed database."""
    if active is RuntimeEnv.PROD or db_host in local_hosts:
        return
    raise ConfigurationError(
        f"The {active.value} environment resolved DB_HOST to {db_host!r}, which "
        f"is not a local database host ({', '.join(sorted(local_hosts))}). "
        f"Deployed credentials belong in {ENV_FILES[RuntimeEnv.PROD]} and are "
        f"selected with `cs2a --env prod` or {ENV_SELECTOR_VAR}=prod."
    )
