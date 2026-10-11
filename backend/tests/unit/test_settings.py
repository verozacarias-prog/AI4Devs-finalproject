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

