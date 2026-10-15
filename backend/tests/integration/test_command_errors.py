"""Cases E12 and E13: an operation command that fails.

It tells the operator what happened with a reference, returns a code that says whether it
refused or failed, and leaves the same log line as any other process.
"""

from __future__ import annotations

import io

import pytest

from app.adapters.inbound.operator_commands.seed_test_data import main
from tests.conftest import UNREACHABLE_DATABASE_URL
from tests.support.log_lines import LogLine, events_of, stack_of

pytestmark = pytest.mark.integration

REFUSED = 1
FAILED = 2


def _run(database_url: str, environment: str) -> tuple[int, str, io.StringIO]:
    output, log = io.StringIO(), io.StringIO()
    code = main({"DATABASE_URL": database_url, "APP_ENV": environment}, output, log)
    return code, output.getvalue(), log


def _reference(line: LogLine) -> str:
    reference = line["request_id"]
    assert isinstance(reference, str)
    return reference


def test_a_refused_command_leaves_its_line_and_gives_the_reference(database_url: str) -> None:
    """Case E12."""
    code, output, log = _run(database_url, "demo")

    assert code == REFUSED
    assert "local" in output
    assert "demo" in output
    errors = events_of(log, "error.expected")
    assert len(errors) == 1
    line = errors[0]
    assert line["process"] == "operator_command"
    assert line["error_code"] == "test_data_not_allowed"
    assert _reference(line) in output
    stack = stack_of(line)
    assert stack[0].startswith("app.adapters.inbound.operator_commands.")
    assert stack[-1].startswith("app.domain.use_cases.seed_test_data:execute:")


def test_a_command_that_fails_says_so_without_the_traceback_or_the_database_url() -> None:
    """Case E13."""
    code, output, log = _run(UNREACHABLE_DATABASE_URL, "local")

    assert code == FAILED
    assert "Traceback" not in output
    assert "127.0.0.1" not in output
    assert "platita:platita" not in output
    errors = events_of(log, "error.unexpected")
    assert len(errors) == 1
    assert errors[0]["process"] == "operator_command"
    assert _reference(errors[0]) in output
