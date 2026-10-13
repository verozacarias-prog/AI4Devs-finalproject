"""Cases E14 and E18: a process that cannot start says which variable is wrong, and no more."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.settings import SettingsError, load_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]


def test_the_api_process_without_the_database_url_ends_with_a_message_and_no_traceback() -> None:
    """Case E14."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "app.main"],
        cwd=BACKEND_DIR,
        env={"PATH": os.environ["PATH"], "APP_ENV": "local"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode != 0
    assert "DATABASE_URL" in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr


def test_without_the_environment_the_process_does_not_start_and_names_the_variable() -> None:
    """Case E18."""
    environ = {"DATABASE_URL": "postgresql+psycopg://u:p@db/platita"}

    with pytest.raises(SettingsError) as error:
        load_settings(environ)

    assert "APP_ENV" in str(error.value)
