"""JSON logs with a filter that lets through only what is known to be safe.

Rules (ADR 0023, docs/operacion.md 6.3):

- The message of a log record is its event name. Only a fixed name such as "http.request"
  passes; any other text, including text built from data, is redacted.
- Only the fields in FIELD_RULES pass, and each one only with its own shape: an integer
  duration, an error class name, a numeric code or a short lowercase word as result, and a
  hexadecimal or UUID identifier. Any other field or value is redacted, so a new field cannot
  leak by omission.
- Of an exception, only the class name is logged: its message and traceback can carry data.

Every logger of the process goes through the same handler, including the web server, the
libraries and Python warnings, because the handler is installed on the root logger. Nothing
below INFO is ever emitted.

Known limit: a value that has the shape of its field passes. An identifier field would let a
32-digit hexadecimal string through whatever it means, so identifiers must be real ids.
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

_EVENT_NAME = re.compile(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+")
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


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _matches(pattern: re.Pattern[str]) -> Callable[[object], bool]:
    return lambda value: isinstance(value, str) and pattern.fullmatch(value) is not None


def _is_result(value: object) -> bool:
    return _is_integer(value) or _matches(_SHORT_WORD)(value)


# The fields that may appear in a log line, each with the only shape it accepts.
FIELD_RULES: dict[str, Callable[[object], bool]] = {
    "message_id": _matches(_IDENTIFIER),
    "request_id": _matches(_IDENTIFIER),
    "user_id": _matches(_IDENTIFIER),
    "duration_ms": _is_integer,
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
        except TypeError, ValueError:
            # A malformed call, such as one with extra arguments. Raising here would make
            # logging dump the message and its arguments to stderr, unfiltered.
            event = REDACTED
        line: dict[str, LogValue] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "process": self._process,
            "version": self._version,
            "logger": record.name,
            "event": event if _EVENT_NAME.fullmatch(event) else REDACTED,
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
