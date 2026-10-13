"""Case E28: a command whose error message cannot be built still ends the way a command does."""

from __future__ import annotations

import io

from app.adapters.inbound.cli.runner import run_command
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
