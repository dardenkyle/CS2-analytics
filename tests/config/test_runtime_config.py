import pytest

from cs2_analytics.config import config
from cs2_analytics.exceptions import ConfigurationError


def test_read_bool_accepts_common_true_and_false_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_FLAG", "yes")
    assert config._read_bool("FEATURE_FLAG", default=False) is True

    monkeypatch.setenv("FEATURE_FLAG", "0")
    assert config._read_bool("FEATURE_FLAG", default=True) is False


def test_read_bool_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_FLAG", "sometimes")

    with pytest.raises(ConfigurationError, match="FEATURE_FLAG must be one of"):
        config._read_bool("FEATURE_FLAG", default=False)


def test_read_int_rejects_non_integer_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "not-a-port")

    with pytest.raises(ConfigurationError, match="API_PORT must be an integer"):
        config._read_int("API_PORT", default=8000)


def test_read_int_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", " 8000 ")

    assert config._read_int("API_PORT", default=9000) == 8000


def test_read_int_rejects_empty_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", " ")

    with pytest.raises(ConfigurationError, match="API_PORT must be an integer"):
        config._read_int("API_PORT", default=8000)


def test_read_csv_rejects_empty_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_CORS_ORIGINS", " , ")

    with pytest.raises(
        ConfigurationError,
        match="API_CORS_ORIGINS must include at least one value",
    ):
        config._read_csv("API_CORS_ORIGINS", default=[])


def test_production_configuration_requires_explicit_runtime_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_var in config.PRODUCTION_REQUIRED_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)

    with pytest.raises(ConfigurationError, match="DB_NAME"):
        config._validate_production_environment(
            environment="production",
            debug_mode=False,
            cors_origins=["https://example.com"],
        )


def test_production_configuration_rejects_debug_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_var in config.PRODUCTION_REQUIRED_ENV_VARS:
        monkeypatch.setenv(env_var, "configured")

    with pytest.raises(ConfigurationError, match="DEBUG_MODE must be false"):
        config._validate_production_environment(
            environment="production",
            debug_mode=True,
            cors_origins=["https://example.com"],
        )


def test_production_configuration_rejects_wildcard_cors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_var in config.PRODUCTION_REQUIRED_ENV_VARS:
        monkeypatch.setenv(env_var, "configured")

    with pytest.raises(ConfigurationError, match="cannot include"):
        config._validate_production_environment(
            environment="production",
            debug_mode=False,
            cors_origins=["*"],
        )


def test_development_configuration_allows_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_var in config.PRODUCTION_REQUIRED_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)

    config._validate_production_environment(
        environment="development",
        debug_mode=True,
        cors_origins=["*"],
    )
