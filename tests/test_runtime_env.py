"""Environment selection: which env file a process reads, and the host guard."""

from pathlib import Path

import pytest

from cs2_analytics import runtime_env
from cs2_analytics.exceptions import ConfigurationError
from cs2_analytics.runtime_env import RuntimeEnv

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "db"})
MARKER = "CS2A_RUNTIME_ENV_TEST_MARKER"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty project root with no environment selected or loaded yet."""
    monkeypatch.setattr(runtime_env, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(runtime_env, "_active", None)
    monkeypatch.delenv(runtime_env.ENV_SELECTOR_VAR, raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    # Registered with monkeypatch so a value loaded from a file is undone.
    monkeypatch.setenv(MARKER, "from-shell")
    return tmp_path


def _write_env_file(project: Path, env: RuntimeEnv, value: str) -> None:
    (project / runtime_env.ENV_FILES[env]).write_text(f"{MARKER}={value}\n")


@pytest.mark.usefixtures("project")
def test_dev_is_the_default_environment() -> None:
    assert runtime_env.resolve_environment() is RuntimeEnv.DEV


@pytest.mark.usefixtures("project")
@pytest.mark.parametrize("env", list(RuntimeEnv))
def test_selector_variable_picks_the_environment(
    monkeypatch: pytest.MonkeyPatch, env: RuntimeEnv
) -> None:
    monkeypatch.setenv(runtime_env.ENV_SELECTOR_VAR, f" {env.value.upper()} ")

    assert runtime_env.resolve_environment() is env


@pytest.mark.usefixtures("project")
def test_selector_variable_rejects_an_unknown_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(runtime_env.ENV_SELECTOR_VAR, "staging")

    with pytest.raises(ConfigurationError, match="must be one of: dev, test, prod"):
        runtime_env.resolve_environment()


@pytest.mark.usefixtures("project")
def test_production_declared_without_an_env_file_is_a_deployed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")

    assert runtime_env.resolve_environment() is RuntimeEnv.PROD


def test_exported_production_does_not_select_prod_when_a_local_env_file_exists(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_env_file(project, RuntimeEnv.DEV, "from-dev-file")
    monkeypatch.setenv("ENVIRONMENT", "production")

    assert runtime_env.resolve_environment() is RuntimeEnv.DEV


def test_selected_file_overrides_a_value_exported_in_the_shell(
    project: Path,
) -> None:
    _write_env_file(project, RuntimeEnv.DEV, "from-dev-file")
    _write_env_file(project, RuntimeEnv.PROD, "from-prod-file")

    assert runtime_env.load_selected_environment() is RuntimeEnv.DEV
    assert runtime_env.os.environ[MARKER] == "from-dev-file"


def test_prod_selection_reads_only_the_production_file(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_env_file(project, RuntimeEnv.DEV, "from-dev-file")
    _write_env_file(project, RuntimeEnv.PROD, "from-prod-file")
    monkeypatch.setenv(runtime_env.ENV_SELECTOR_VAR, "prod")

    assert runtime_env.load_selected_environment() is RuntimeEnv.PROD
    assert runtime_env.os.environ[MARKER] == "from-prod-file"


def test_environment_file_is_loaded_once_per_process(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_env_file(project, RuntimeEnv.DEV, "from-dev-file")
    runtime_env.load_selected_environment()
    monkeypatch.setenv(MARKER, "changed-after-load")
    monkeypatch.setenv(runtime_env.ENV_SELECTOR_VAR, "prod")

    # A config reload must not re-apply the file or switch environments.
    assert runtime_env.load_selected_environment() is RuntimeEnv.DEV
    assert runtime_env.os.environ[MARKER] == "changed-after-load"


@pytest.mark.parametrize("env", list(RuntimeEnv))
def test_leftover_unnamed_env_file_is_rejected_for_every_environment(
    project: Path, monkeypatch: pytest.MonkeyPatch, env: RuntimeEnv
) -> None:
    _write_env_file(project, env, "from-named-file")
    (project / runtime_env.LEGACY_ENV_FILE).write_text(f"{MARKER}=from-legacy\n")
    monkeypatch.setenv(runtime_env.ENV_SELECTOR_VAR, env.value)

    with pytest.raises(ConfigurationError, match="is no longer read") as error:
        runtime_env.load_selected_environment()

    assert ".env.dev" in str(error.value)
    assert ".env.prod" in str(error.value)
    assert runtime_env.os.environ[MARKER] == "from-shell"


@pytest.mark.usefixtures("project")
def test_dev_runs_on_defaults_when_its_file_is_missing() -> None:
    assert runtime_env.load_selected_environment() is RuntimeEnv.DEV
    assert runtime_env.os.environ[MARKER] == "from-shell"


@pytest.mark.usefixtures("project")
@pytest.mark.parametrize("env", [RuntimeEnv.TEST, RuntimeEnv.PROD])
def test_explicit_selection_requires_its_env_file(
    monkeypatch: pytest.MonkeyPatch, env: RuntimeEnv
) -> None:
    monkeypatch.setenv(runtime_env.ENV_SELECTOR_VAR, env.value)

    with pytest.raises(ConfigurationError, match="does not exist"):
        runtime_env.load_selected_environment()


@pytest.mark.usefixtures("project")
def test_deployed_runtime_loads_without_an_env_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")

    assert runtime_env.load_selected_environment() is RuntimeEnv.PROD
    assert runtime_env.os.environ[MARKER] == "from-shell"


@pytest.mark.parametrize("env", [RuntimeEnv.DEV, RuntimeEnv.TEST])
def test_dev_and_test_refuse_a_non_local_database_host(env: RuntimeEnv) -> None:
    with pytest.raises(ConfigurationError, match="not a local database host") as error:
        runtime_env.refuse_non_local_host(env, "db.example.com", LOCAL_HOSTS)

    assert "cs2a --env prod" in str(error.value)


@pytest.mark.parametrize("host", sorted(LOCAL_HOSTS))
def test_dev_accepts_every_local_database_host(host: str) -> None:
    runtime_env.refuse_non_local_host(RuntimeEnv.DEV, host, LOCAL_HOSTS)


def test_prod_accepts_a_non_local_database_host() -> None:
    runtime_env.refuse_non_local_host(RuntimeEnv.PROD, "db.example.com", LOCAL_HOSTS)
