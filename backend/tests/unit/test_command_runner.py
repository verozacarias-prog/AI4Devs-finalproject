"""Case E28: a command whose error message cannot be built still ends the way a command does."""

from __future__ import annotations

import io

from app.adapters.inbound.operator_commands.runner import run_command
from app.domain.errors import ForbiddenError
from app.settings import Settings

REFUSED = 1


def _refuses_without_context(settings: Settings) -> str:
    # The message of this code needs the environment, which this error does not carry.
    raise ForbiddenError("test_data_not_allowed")


def test_an_error_without_the_data_its_message_needs_gets_the_generic_one() -> None:
    output = io.StringIO()
    environ = {"DATABASE_URL": "postgresql+psycopg://u:p@db/platita", "APP_ENV": "production"}

    code = run_command(_refuses_without_context, environ, output, io.StringIO())

    written = output.getvalue()
    assert code == REFUSED
    assert "test_data_not_allowed" in written
    assert "Reference: " in written
    assert "Traceback" not in written


FAILED = 2


def test_no_command_runs_with_the_development_entry_enabled_in_production() -> None:
    """Case 20 of the development entry: every process reads the same settings."""
    ran: list[Settings] = []

    def command(settings: Settings) -> str:
        ran.append(settings)
        return "done"

    output = io.StringIO()
    environ = {
        "DATABASE_URL": "postgresql+psycopg://u:p@db/platita",
        "APP_ENV": "production",
        "DEV_ENTRY_ENABLED": "true",
    }

    code = run_command(command, environ, output, io.StringIO())

    assert code == FAILED
    assert ran == []
    assert "DEV_ENTRY_ENABLED" in output.getvalue()
