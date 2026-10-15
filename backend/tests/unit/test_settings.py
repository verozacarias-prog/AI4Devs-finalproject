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
