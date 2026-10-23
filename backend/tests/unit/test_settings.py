"""Case 7: without the database URL, the process does not start."""

from __future__ import annotations

import pytest

from app.settings import SettingsError, load_settings


def test_missing_database_url_stops_startup_and_names_the_variable() -> None:
    environ = {"APP_ENV": "local", "SOME_API_KEY": "s3cr3t-value"}

    with pytest.raises(SettingsError) as error:
        load_settings(environ)

    message = str(error.value)
    assert "DATABASE_URL" in message
    assert "s3cr3t-value" not in message


def test_an_unknown_environment_stops_startup_and_names_the_variable() -> None:
    """Case 18."""
    environ = {"DATABASE_URL": "postgresql+psycopg://u:p@db/platita", "APP_ENV": "staging"}

    with pytest.raises(SettingsError) as error:
        load_settings(environ)

    assert "APP_ENV" in str(error.value)


BASE_ENVIRON = {"DATABASE_URL": "postgresql+psycopg://u:p@db/platita", "APP_ENV": "local"}


@pytest.mark.parametrize("environment", ["local", "demo", "production"])
def test_without_its_variable_the_development_entry_is_off(environment: str) -> None:
    """Case 17 of the development entry."""
    settings = load_settings(BASE_ENVIRON | {"APP_ENV": environment})

    assert settings.dev_entry_enabled is False


@pytest.mark.parametrize(("value", "enabled"), [("true", True), ("false", False)])
def test_the_development_entry_is_what_its_variable_says(value: str, enabled: bool) -> None:
    """Case 18 of the development entry."""
    settings = load_settings(BASE_ENVIRON | {"DEV_ENTRY_ENABLED": value})

    assert settings.dev_entry_enabled is enabled


def test_a_value_that_is_neither_true_nor_false_stops_startup() -> None:
    """Case 19 of the development entry."""
    with pytest.raises(SettingsError) as error:
        load_settings(BASE_ENVIRON | {"DEV_ENTRY_ENABLED": "yes"})

    message = str(error.value)
    assert "DEV_ENTRY_ENABLED" in message
    assert "true" in message
    assert "false" in message
    assert "yes" not in message


def test_the_development_entry_enabled_in_production_stops_startup() -> None:
    """Case 20 of the development entry."""
    environ = BASE_ENVIRON | {"APP_ENV": "production", "DEV_ENTRY_ENABLED": "true"}

    with pytest.raises(SettingsError) as error:
        load_settings(environ)

    message = str(error.value)
    assert "DEV_ENTRY_ENABLED" in message
    assert "production" in message


def test_the_web_chat_enabled_in_production_stops_startup() -> None:
    """Case C2-18 of FEAT-002."""
    environ = BASE_ENVIRON | {"APP_ENV": "production", "WEB_CHAT_ENABLED": "true"}

    with pytest.raises(SettingsError) as error:
        load_settings(environ)

    message = str(error.value)
    assert message == "WEB_CHAT_ENABLED cannot be enabled in the production environment"


@pytest.mark.parametrize("variable", ["QUEUE_MAX_WAIT_MINUTES", "WORKER_LOCK_SECONDS"])
@pytest.mark.parametrize("value", ["0", "-5", "diez", "1.5"])
def test_a_wait_or_a_lock_that_is_not_a_positive_integer_stops_startup(
    variable: str, value: str
) -> None:
    """Case C3-17 of FEAT-002."""
    with pytest.raises(SettingsError) as error:
        load_settings(BASE_ENVIRON | {variable: value})

    message = str(error.value)
    assert variable in message
    assert value not in message


def test_with_the_lock_not_longer_than_the_call_no_process_starts() -> None:
    """Case C2-34 of FEAT-003: the call must end before another worker can take the message."""
    with pytest.raises(SettingsError) as error:
        load_settings(BASE_ENVIRON | {"WORKER_LOCK_SECONDS": "30", "LLM_TIMEOUT_SECONDS": "30"})

    message = str(error.value)
    assert "WORKER_LOCK_SECONDS" in message
    assert "LLM_TIMEOUT_SECONDS" in message
    settings = load_settings(
        BASE_ENVIRON | {"WORKER_LOCK_SECONDS": "31", "LLM_TIMEOUT_SECONDS": "30"}
    )
    assert settings.worker_lock_seconds == 31


def test_the_limits_come_from_the_configuration() -> None:
    """Case C3-10 of FEAT-003: they change without deploying, by restarting the process."""
    settings = load_settings(
        BASE_ENVIRON
        | {"LLM_DAILY_CLASSIFICATION_LIMIT": "30", "LLM_DAILY_REGISTRATION_LIMIT": "20"}
    )
    assert settings.llm_daily_classification_limit == 30
    assert settings.llm_daily_registration_limit == 20

    defaults = load_settings(BASE_ENVIRON)
    assert defaults.llm_daily_classification_limit == 100
    assert defaults.llm_daily_registration_limit == 50


@pytest.mark.parametrize(
    "variable", ["LLM_DAILY_CLASSIFICATION_LIMIT", "LLM_DAILY_REGISTRATION_LIMIT"]
)
@pytest.mark.parametrize("value", ["0", "-1", "diez"])
def test_a_limit_that_is_not_a_positive_integer_stops_startup(variable: str, value: str) -> None:
    """Case C3-10 of FEAT-003."""
    with pytest.raises(SettingsError) as error:
        load_settings(BASE_ENVIRON | {variable: value})

    message = str(error.value)
    assert variable in message
    assert value not in message
