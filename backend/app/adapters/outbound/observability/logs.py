"""JSON logs with a filter that lets through only what is known to be safe.

Rules (ADR 0023, docs/operacion.md 6.3):

- The message of a log record is its event name. Only a fixed name such as "http.request"
  passes: dotted lowercase words, each starting with a letter, up to MAX_EVENT_LENGTH
  characters. Any other text, including text built from data, is redacted.
- Only the fields in FIELD_RULES pass, and each one only with its own shape: a duration
  between zero and an hour, an error class name, a code between 100 and 599 or a short
  lowercase word as result, and a hexadecimal or UUID identifier. Any other field or value
  is redacted, so a new field cannot leak by omission.
- Of an exception, only the class name is logged: its message and traceback can carry data.
  An error adds what locates it without a value: its code, its path through the code, the
  class it was translated from, the constraint that rejected a write, the identifiers of what
  it was touching and its catalog values.

Every logger of the process goes through the same handler, including the web server, the
libraries and Python warnings, because the handler is installed on the root logger. Nothing
below INFO is ever emitted.

A record is never lost in silence: if its message cannot be built, the line is still written,
with the event redacted.

Known limit: a value that has the shape of its place passes. An identifier field lets through
any 32-digit hexadecimal string, and a message made of lowercase words passes as an event
name, so identifiers must be real ids and event names must be constants in the code.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO

from app.adapters.outbound.observability.events import (
    CLASS_NAME_PATTERN,
    CODE_PLACE_PATTERN,
    CONSTRAINT_PATTERN,
    CURRENCY_CODE_PATTERN,
    EVENT_NAME_PATTERN,
    HANDLER_NAME,
    IDENTIFIER_FIELD_SUFFIX,
    IDENTIFIER_PATTERN,
    MAX_DURATION_MS,
    MAX_EVENT_LENGTH,
    MAX_RESULT_CODE,
    MAX_STACK_DEPTH,
    MIN_RESULT_CODE,
    REDACTED,
    SHORT_WORD_PATTERN,
    Field,
    LineKey,
    LoggerName,
)
from app.constants import ProcessName
from app.domain.errors import ContextField

__all__ = ["REDACTED", "build_handler", "configure_logging", "request_id_var"]

LogValue = str | int | float | bool | list[str] | None

# Identifier of the API request being served. A request that is not a message gets one when
# it arrives; the worker will set the message id the same way.
request_id_var: ContextVar[str | None] = ContextVar(Field.REQUEST_ID, default=None)

_EVENT_NAME = re.compile(EVENT_NAME_PATTERN)
_IDENTIFIER = re.compile(IDENTIFIER_PATTERN)
_CLASS_NAME = re.compile(CLASS_NAME_PATTERN)
_SHORT_WORD = re.compile(SHORT_WORD_PATTERN)
_CONSTRAINT = re.compile(CONSTRAINT_PATTERN)
_CODE_PLACE = re.compile(CODE_PLACE_PATTERN)
_CURRENCY_CODE = re.compile(CURRENCY_CODE_PATTERN)
# The attributes every record has, as the logging library names them.
_RECORD_ATTRIBUTES = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


def _extra_fields(record: logging.LogRecord) -> list[str]:
    return [name for name in record.__dict__ if name not in _RECORD_ATTRIBUTES]


def _is_integer_between(low: int, high: int) -> Callable[[object], bool]:
    def check(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high

    return check


def _matches(pattern: re.Pattern[str]) -> Callable[[object], bool]:
    return lambda value: isinstance(value, str) and pattern.fullmatch(value) is not None


def _is_result(value: object) -> bool:
    return _is_integer_between(MIN_RESULT_CODE, MAX_RESULT_CODE)(value) or _matches(_SHORT_WORD)(
        value
    )


def _is_code_path(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= MAX_STACK_DEPTH
        and all(_matches(_CODE_PLACE)(place) for place in value)
    )


def _is_catalog_value(value: object) -> bool:
    return _matches(_SHORT_WORD)(value) or _matches(_CURRENCY_CODE)(value)


# The fields that may appear in a log line, each with the only shape it accepts.
FIELD_RULES: dict[str, Callable[[object], bool]] = {
    Field.DURATION_MS: _is_integer_between(0, MAX_DURATION_MS),
    Field.RESULT: _is_result,
    Field.ERROR_TYPE: _matches(_CLASS_NAME),
    Field.ERROR_CODE: _matches(_SHORT_WORD),
    Field.ERROR_STACK: _is_code_path,
    Field.ERROR_CAUSE: _matches(_CLASS_NAME),
    Field.CONSTRAINT: _matches(_CONSTRAINT),
    **dict.fromkeys(ContextField, _is_catalog_value),
}


def _rule_for(name: str) -> Callable[[object], bool] | None:
    if name.endswith(IDENTIFIER_FIELD_SUFFIX):
        return _matches(_IDENTIFIER)
    return FIELD_RULES.get(name)


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for name in _extra_fields(record):
            value = record.__dict__[name]
            if value is None:
                continue
            rule = _rule_for(name)
            if rule is None or not rule(value):
                record.__dict__[name] = REDACTED
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, version: str, process: str) -> None:
        super().__init__()
        self._version = version
        self._process = process

    def format(self, record: logging.LogRecord) -> str:
        try:
            event = record.getMessage()
        except Exception:
            # A malformed call, or a value that fails when turned into text. Raising here
            # would lose the record, or make logging dump it to stderr unfiltered.
            event = REDACTED
        if len(event) > MAX_EVENT_LENGTH or not _EVENT_NAME.fullmatch(event):
            event = REDACTED
        line: dict[str, LogValue] = {
            LineKey.TIMESTAMP: datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            LineKey.LEVEL: record.levelname,
            LineKey.PROCESS: self._process,
            LineKey.VERSION: self._version,
            LineKey.LOGGER: record.name,
            LineKey.EVENT: event,
            Field.REQUEST_ID: request_id_var.get(),
        }
        for name in _extra_fields(record):
            line[name] = record.__dict__[name]
        if record.exc_info and record.exc_info[0] is not None:
            line[Field.ERROR_TYPE] = record.exc_info[0].__name__
        return json.dumps(line, ensure_ascii=False)


def build_handler(stream: TextIO, version: str, process: str = ProcessName.API) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.set_name(HANDLER_NAME)
    # Even if a library sets its own logger to DEBUG, the line is not emitted.
    handler.setLevel(logging.INFO)
    handler.addFilter(RedactionFilter())
    handler.setFormatter(JsonFormatter(version, process))
    return handler


def configure_logging(stream: TextIO, version: str, process: str = ProcessName.API) -> None:
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if h.get_name() != HANDLER_NAME]
    root.addHandler(build_handler(stream, version, process))
    # Libraries log from WARNING up; the application and the server, from INFO. DEBUG is
    # where payloads end up dumped, so it is never enabled.
    root.setLevel(logging.WARNING)
    logging.getLogger(LoggerName.APP).setLevel(logging.INFO)
    # If a handler ever fails, logging must not print the record to stderr on its own.
    logging.raiseExceptions = False
    # Python warnings become log records of "py.warnings" instead of raw text on stderr.
    # Turned off first so that calling this twice installs the hook again instead of
    # trusting a previous installation that something else may have undone.
    logging.captureWarnings(False)
    logging.captureWarnings(True)

    # However the server was started, its lines go to the root handler and nowhere else.
    for name in (LoggerName.SERVER, LoggerName.SERVER_ERROR):
        server_logger = logging.getLogger(name)
        server_logger.handlers = []
        server_logger.propagate = True
        server_logger.setLevel(logging.INFO)
    # The web server logs every access with the client IP; that log is turned off.
    access_logger = logging.getLogger(LoggerName.SERVER_ACCESS)
    access_logger.handlers = []
    access_logger.disabled = True
