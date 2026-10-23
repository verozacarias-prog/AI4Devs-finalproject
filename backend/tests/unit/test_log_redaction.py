"""Cases 10 to 13, 15, 16 and 20 to 27, and C3-22 of FEAT-002: what the log filter lets through.

Only allowed fields pass, and only a fixed event name passes as the message; everything else
is redacted (docs/operacion.md, 6.3).
"""

from __future__ import annotations

import io
import json
import logging
import uuid
import warnings
from collections.abc import Iterator
from decimal import Decimal

import pytest

from app.adapters.observability.logs import (
    REDACTED,
    build_handler,
    configure_logging,
    message_id_var,
    request_id_var,
    user_id_var,
)

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


def test_a_message_built_from_data_is_redacted(logger: logging.Logger, stream: io.StringIO) -> None:
    """Case 13."""
    logger.info("paid %s from %s", "58400", "Galicia")

    raw, line = only_line(stream)
    assert line["event"] == REDACTED
    assert "58400" not in raw
    assert "Galicia" not in raw


def test_free_text_in_an_allowed_field_is_redacted(
    logger: logging.Logger, stream: io.StringIO
) -> None:
    """Case 15."""
    logger.info("transaction.registered", extra={"result": "Gasté 58.400 en el super"})

    raw, line = only_line(stream)
    assert line["result"] == REDACTED
    assert "58.400" not in raw


@pytest.mark.parametrize("value", ["ok", 200])
def test_a_short_value_in_an_allowed_field_passes(
    logger: logging.Logger, stream: io.StringIO, value: str | int
) -> None:
    """Case 15."""
    logger.info("transaction.registered", extra={"result": value})

    _, line = only_line(stream)
    assert line["result"] == value


def test_other_libraries_go_through_the_same_filter(stream: io.StringIO) -> None:
    """Case 16."""
    root = logging.getLogger()
    previous = list(root.handlers)
    try:
        configure_logging(stream, version="test")
        logging.getLogger("sqlalchemy.engine").warning(
            "INSERT INTO app_user (phone, amount) VALUES (%s, %s) [parameters: %s]",
            "phone",
            "amount",
            ("+5491155551234", "58400.00"),
        )
    finally:
        root.handlers = previous

    raw, line = only_line(stream)
    assert line["event"] == REDACTED
    assert line["logger"] == "sqlalchemy.engine"
    assert "5491155551234" not in raw
    assert "58400" not in raw


@pytest.fixture
def process_logging(stream: io.StringIO) -> Iterator[None]:
    """The logging of the whole process, as the API configures it, undone afterwards."""
    root = logging.getLogger()
    previous_handlers, previous_level = list(root.handlers), root.level
    try:
        configure_logging(stream, version="test")
        yield
    finally:
        logging.captureWarnings(False)
        root.handlers = previous_handlers
        root.setLevel(previous_level)


def test_a_malformed_log_call_does_not_dump_its_arguments(
    logger: logging.Logger, stream: io.StringIO, capsys: pytest.CaptureFixture[str]
) -> None:
    """Case 20."""
    logger.info("paid %s", "58400", "+5491155551234")

    raw, line = only_line(stream)
    assert line["event"] == REDACTED
    for output in (raw, capsys.readouterr().err):
        assert "58400" not in output
        assert "5491155551234" not in output


@pytest.mark.usefixtures("process_logging")
def test_python_warnings_go_through_the_filter(
    stream: io.StringIO, capsys: pytest.CaptureFixture[str]
) -> None:
    """Case 21."""
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        warnings.warn("slow query for user +5491155551234", stacklevel=1)

    raw, line = only_line(stream)
    assert line["event"] == REDACTED
    assert line["logger"] == "py.warnings"
    assert "5491155551234" not in raw
    assert "5491155551234" not in capsys.readouterr().err


@pytest.mark.usefixtures("process_logging")
def test_debug_is_never_emitted(stream: io.StringIO) -> None:
    """Case 22."""
    library = logging.getLogger("some_library")
    library.setLevel(logging.DEBUG)
    try:
        library.debug("payload.dumped")
    finally:
        library.setLevel(logging.NOTSET)

    assert stream.getvalue() == ""


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_ms", 58400.5),
        ("error_type", "190.12.33.7"),
        ("result", "58400.00"),
        ("user_id", "Galicia"),
    ],
)
def test_an_allowed_field_with_the_wrong_shape_is_redacted(
    logger: logging.Logger, stream: io.StringIO, field: str, value: str | float
) -> None:
    """Case 23."""
    logger.info("some.event", extra={field: value})

    raw, line = only_line(stream)
    assert line[field] == REDACTED
    assert str(value) not in raw


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_ms", 12),
        ("error_type", "OperationalError"),
        ("result", 200),
        ("result", "ok"),
        ("request_id", uuid.UUID(int=7).hex),
        ("message_id", str(uuid.UUID(int=7))),
    ],
)
def test_an_allowed_field_with_its_own_shape_passes(
    logger: logging.Logger, stream: io.StringIO, field: str, value: str | int
) -> None:
    """Case 23."""
    logger.info("some.event", extra={field: value})

    _, line = only_line(stream)
    assert line[field] == value


def test_a_value_that_is_neither_text_nor_number_is_redacted(
    logger: logging.Logger, stream: io.StringIO
) -> None:
    """Case 24."""
    logger.info("some.event", extra={"result": Decimal("58400.00")})

    raw, line = only_line(stream)
    assert line["result"] == REDACTED
    assert "58400" not in raw


@pytest.mark.parametrize("message", ["user.5491155551234", "paid.58400", "ip.190_12_33_7"])
def test_data_shaped_like_an_event_name_is_redacted(
    logger: logging.Logger, stream: io.StringIO, message: str
) -> None:
    """Case 25."""
    logger.info(message)

    raw, line = only_line(stream)
    assert line["event"] == REDACTED
    assert message not in raw


def test_an_event_name_longer_than_the_limit_is_redacted(
    logger: logging.Logger, stream: io.StringIO
) -> None:
    """Case 25."""
    logger.info("a." + "b" * 80)

    _, line = only_line(stream)
    assert line["event"] == REDACTED


class _FailsAsText:
    def __str__(self) -> str:
        raise RuntimeError("58400")


def test_a_record_with_a_missing_format_key_still_leaves_a_line(
    logger: logging.Logger, stream: io.StringIO, capsys: pytest.CaptureFixture[str]
) -> None:
    """Case 26."""
    logger.info("paid %(amount)s", {"total": "58400"})

    raw, line = only_line(stream)
    assert line["event"] == REDACTED
    assert "58400" not in raw
    assert "58400" not in capsys.readouterr().err


def test_a_value_that_fails_as_text_still_leaves_a_line(
    logger: logging.Logger, stream: io.StringIO, capsys: pytest.CaptureFixture[str]
) -> None:
    """Case 26."""
    logger.info("paid %s", _FailsAsText())

    raw, line = only_line(stream)
    assert line["event"] == REDACTED
    assert "58400" not in raw
    assert "58400" not in capsys.readouterr().err


@pytest.mark.parametrize(("field", "value"), [("result", 5491155551234), ("duration_ms", -987654)])
def test_a_number_out_of_range_is_redacted(
    logger: logging.Logger, stream: io.StringIO, field: str, value: int
) -> None:
    """Case 27."""
    logger.info("some.event", extra={field: value})

    raw, line = only_line(stream)
    assert line[field] == REDACTED
    assert str(value) not in raw


@pytest.mark.parametrize(
    ("field", "value"),
    [("result", 100), ("result", 599), ("duration_ms", 0), ("duration_ms", 3_600_000)],
)
def test_a_number_in_range_passes(
    logger: logging.Logger, stream: io.StringIO, field: str, value: int
) -> None:
    """Case 27."""
    logger.info("some.event", extra={field: value})

    _, line = only_line(stream)
    assert line[field] == value


def _line_with_context(
    logger: logging.Logger, stream: io.StringIO, request_id: str, message_id: str, user_id: str
) -> tuple[str, JsonLine]:
    """A line written while the process holds those identifiers of the request, message and user."""
    tokens = (
        request_id_var.set(request_id),
        message_id_var.set(message_id),
        user_id_var.set(user_id),
    )
    try:
        logger.info("message.answered")
    finally:
        request_id_var.reset(tokens[0])
        message_id_var.reset(tokens[1])
        user_id_var.reset(tokens[2])
    return only_line(stream)


def test_the_identifiers_of_the_context_also_go_through_the_filter(
    logger: logging.Logger, stream: io.StringIO
) -> None:
    # Case C3-22 of FEAT-002.
    not_identifiers = ("+000000000001", "gasté 3500 en el súper", "Lucía")

    raw, line = _line_with_context(logger, stream, *not_identifiers)

    assert (line["request_id"], line["message_id"], line["user_id"]) == (REDACTED,) * 3
    for text in not_identifiers:
        assert text not in raw

    identifiers = tuple(str(uuid.uuid4()) for _ in range(3))
    stream.truncate(0)
    stream.seek(0)

    _, line = _line_with_context(logger, stream, *identifiers)

    assert (line["request_id"], line["message_id"], line["user_id"]) == identifiers
