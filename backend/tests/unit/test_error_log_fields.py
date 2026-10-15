"""Case E11: the fields of an error pass the log filter only with their own shape."""

from __future__ import annotations

import io
import json
import logging

import pytest

from app.adapters.observability.logs import REDACTED, build_handler

Value = str | list[str]


@pytest.fixture
def stream() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def logger(stream: io.StringIO) -> logging.Logger:
    test_logger = logging.getLogger("platita.test.error_fields")
    test_logger.handlers = [build_handler(stream, version="test")]
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False
    return test_logger


def _logged(logger: logging.Logger, stream: io.StringIO, field: str, value: Value) -> Value:
    logger.error("error.unexpected", extra={field: value})
    lines = stream.getvalue().splitlines()
    assert len(lines) == 1
    logged: Value = json.loads(lines[0])[field]
    return logged


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("error_code", "period_overlaps"),
        ("error_cause", "IntegrityError"),
        ("constraint", "uq_app_user_whatsapp_phone"),
        ("account_id", "0b3d5c1e-6f0a-4c57-9b1e-2f6a8d4c7e10"),
        ("budget_period_id", "0b3d5c1e6f0a4c579b1e2f6a8d4c7e10"),
        ("environment", "demo"),
        (
            "error_stack",
            [
                "app.adapters.inbound.operator_commands.seed_test_data:main:34",
                "app.domain.use_cases.seed_test_data:execute:56",
            ],
        ),
    ],
)
def test_a_field_with_its_own_shape_passes(
    logger: logging.Logger, stream: io.StringIO, field: str, value: Value
) -> None:
    assert _logged(logger, stream, field, value) == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("error_code", "Could not register 58400"),
        ("error_cause", "duplicate key (+5491155551234)"),
        ("constraint", "Key (whatsapp_phone)=(+5491155551234)"),
        ("constraint", "c" * 64),
        ("account_id", "Galicia pesos"),
        ("budget_period_id", "58400"),
        ("environment", "gasté 58400 en el súper"),
        ("transaction_type", "expense"),
        ("currency", "ARS"),
        ("error_stack", ["could not register 58400 for +5491155551234"]),
        ("error_stack", "could not register 58400"),
        ("error_message", "could not register 58400"),
    ],
)
def test_a_field_with_any_other_shape_is_redacted(
    logger: logging.Logger, stream: io.StringIO, field: str, value: Value
) -> None:
    assert _logged(logger, stream, field, value) == REDACTED
    assert "58400" not in stream.getvalue()
    assert "5491155551234" not in stream.getvalue()
