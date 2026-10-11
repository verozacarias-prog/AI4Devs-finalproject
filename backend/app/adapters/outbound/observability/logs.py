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

LOGGER_NAME = "platita"
REDACTED = "[redacted]"

LogValue = str | int | float | bool | None

# Identifier of the API request being served. A request that is not a message gets one when
# it arrives; the worker will set the message id the same way.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

MAX_EVENT_LENGTH = 64
MAX_DURATION_MS = 3_600_000

_EVENT_NAME = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+")
_IDENTIFIER = re.compile(r"[0-9a-f]{32}|[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
_CLASS_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
_SHORT_WORD = re.compile(r"[a-z][a-z_]{0,31}")
_RECORD_ATTRIBUTES = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
_HANDLER_NAME = "platita-json"
# The web server logs every access with the client IP; that log is turned off.
_SERVER_ACCESS_LOGGER = "uvicorn.access"
_SERVER_LOGGERS = ("uvicorn", "uvicorn.error")


def _extra_fields(record: logging.LogRecord) -> list[str]:
    return [name for name in record.__dict__ if name not in _RECORD_ATTRIBUTES]


def _is_integer_between(low: int, high: int) -> Callable[[object], bool]:
    def check(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high

    return check


def _matches(pattern: re.Pattern[str]) -> Callable[[object], bool]:
    return lambda value: isinstance(value, str) and pattern.fullmatch(value) is not None


def _is_result(value: object) -> bool:
    return _is_integer_between(100, 599)(value) or _matches(_SHORT_WORD)(value)


# The fields that may appear in a log line, each with the only shape it accepts.
FIELD_RULES: dict[str, Callable[[object], bool]] = {
    "message_id": _matches(_IDENTIFIER),
    "request_id": _matches(_IDENTIFIER),
    "user_id": _matches(_IDENTIFIER),
    "duration_ms": _is_integer_between(0, MAX_DURATION_MS),
    "result": _is_result,
    "error_type": _matches(_CLASS_NAME),
}


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for name in _extra_fields(record):
            value = record.__dict__[name]
            if value is None:
                continue
            rule = FIELD_RULES.get(name)
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
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "process": self._process,
            "version": self._version,
            "logger": record.name,
            "event": event,
            "request_id": request_id_var.get(),
        }
        for name in _extra_fields(record):
            line[name] = record.__dict__[name]
        if record.exc_info and record.exc_info[0] is not None:
            line["error_type"] = record.exc_info[0].__name__
        return json.dumps(line, ensure_ascii=False)


def build_handler(stream: TextIO, version: str, process: str = "api") -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.set_name(_HANDLER_NAME)
    # Even if a library sets its own logger to DEBUG, the line is not emitted.
    handler.setLevel(logging.INFO)
    handler.addFilter(RedactionFilter())
    handler.setFormatter(JsonFormatter(version, process))
    return handler


def configure_logging(stream: TextIO, version: str, process: str = "api") -> None:
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if h.get_name() != _HANDLER_NAME]
    root.addHandler(build_handler(stream, version, process))
    # Libraries log from WARNING up; the application and the server, from INFO. DEBUG is
    # where payloads end up dumped, so it is never enabled.
    root.setLevel(logging.WARNING)
    logging.getLogger(LOGGER_NAME).setLevel(logging.INFO)
    # If a handler ever fails, logging must not print the record to stderr on its own.
    logging.raiseExceptions = False
    # Python warnings become log records of "py.warnings" instead of raw text on stderr.
    # Turned off first so that calling this twice installs the hook again instead of
    # trusting a previous installation that something else may have undone.
    logging.captureWarnings(False)
    logging.captureWarnings(True)

    # However the server was started, its lines go to the root handler and nowhere else.
    for name in _SERVER_LOGGERS:
        server_logger = logging.getLogger(name)
        server_logger.handlers = []
        server_logger.propagate = True
        server_logger.setLevel(logging.INFO)
    access_logger = logging.getLogger(_SERVER_ACCESS_LOGGER)
    access_logger.handlers = []
    access_logger.disabled = True
