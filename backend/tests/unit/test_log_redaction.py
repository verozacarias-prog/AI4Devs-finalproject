"""Cases 10, 11 and 12: the log filter redacts by field name.

Only allowed fields pass; everything else is redacted (docs/operacion.md, 6.3).
"""
from __future__ import annotations

import io
import json
import logging

import pytest

from app.adapters.outbound.observability.logs import REDACTED, build_handler

JsonLine = dict[str, str | int | float | bool | None]


@pytest.fixture
def stream() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def logger(stream: io.StringIO) -> logging.Logger:
    test_logger = logging.getLogger("platita.test.redaction")
    test_logger.handlers = [build_handler(stream, version="test")]
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False
    return test_logger


def only_line(stream: io.StringIO) -> tuple[str, JsonLine]:
    lines = stream.getvalue().splitlines()
    assert len(lines) == 1
    parsed: JsonLine = json.loads(lines[0])
    return lines[0], parsed


def test_personal_data_fields_are_redacted_and_the_rest_stays(
    logger: logging.Logger, stream: io.StringIO
) -> None:
    logger.info(
        "transaction.registered",
        extra={
            "phone": "+5491155551234",
            "amount": "58400.00",
            "text": "Gasté 58.400 en el super con la Galicia",
            "account_name": "Galicia ARS",
            "duration_ms": 12,
            "result": "ok",
        },
    )

    raw, line = only_line(stream)
    for field in ("phone", "amount", "text", "account_name"):
        assert line[field] == REDACTED
    for value in ("5491155551234", "58400", "58.400", "Galicia"):
        assert value not in raw
    assert line["event"] == "transaction.registered"
    assert line["duration_ms"] == 12
    assert line["result"] == "ok"


def test_credential_fields_are_redacted(logger: logging.Logger, stream: io.StringIO) -> None:
    logger.info(
        "auth.session_created",
        extra={
            "code": "482913",
            "cookie": "__Host-sid=abc123def456",
            "token": "tok_9f8e7d6c",
            "database_url": "postgresql://platita:hunter2@db/platita",
        },
    )

    raw, line = only_line(stream)
    for field in ("code", "cookie", "token", "database_url"):
        assert line[field] == REDACTED
    for value in ("482913", "abc123def456", "tok_9f8e7d6c", "hunter2"):
        assert value not in raw


def test_an_unknown_field_is_redacted_too(logger: logging.Logger, stream: io.StringIO) -> None:
    logger.info("some.event", extra={"brand_new_field": "value-nobody-listed"})

    raw, line = only_line(stream)
    assert line["brand_new_field"] == REDACTED
    assert "value-nobody-listed" not in raw
