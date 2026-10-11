"""JSON logs with a filter that redacts by field name (ADR 0023, docs/operacion.md 6.3).

Only the fields in ALLOWED_FIELDS pass. Any other field attached to a log record is replaced
by REDACTED, so a new field cannot leak personal data by omission. The event name is the log
message: it must be a fixed name such as "http.request", never text built from user data.
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO

LOGGER_NAME = "platita"
SERVER_LOGGER_NAME = "uvicorn"
REDACTED = "[redacted]"
ALLOWED_FIELDS = frozenset({"message_id", "request_id", "user_id", "duration_ms", "result"})

LogValue = str | int | float | bool | None

# Identifier of the API request being served. A request that is not a message gets one when
# it arrives; the worker will set the message id the same way.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_RECORD_ATTRIBUTES = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


def _extra_fields(record: logging.LogRecord) -> list[str]:
    return [name for name in record.__dict__ if name not in _RECORD_ATTRIBUTES]


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for name in _extra_fields(record):
            value = record.__dict__[name]
            allowed = name in ALLOWED_FIELDS and isinstance(value, str | int | float | bool)
            if not allowed and value is not None:
                record.__dict__[name] = REDACTED
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, version: str, process: str) -> None:
        super().__init__()
        self._version = version
        self._process = process

    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, LogValue] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "process": self._process,
            "version": self._version,
            "event": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for name in _extra_fields(record):
            line[name] = record.__dict__[name]
        if record.exc_info and record.exc_info[0] is not None:
            # Only the exception class: its message and traceback can carry user data.
            line["error_type"] = record.exc_info[0].__name__
        return json.dumps(line, ensure_ascii=False)


def build_handler(stream: TextIO, version: str, process: str = "api") -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.addFilter(RedactionFilter())
    handler.setFormatter(JsonFormatter(version, process))
    return handler


def configure_logging(stream: TextIO, version: str, process: str = "api") -> logging.Logger:
    handler = build_handler(stream, version, process)
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers = [handler]
    # INFO everywhere. DEBUG is where payloads end up dumped, so it is never enabled.
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # The server's own start-up and error lines go through the same handler, so every line
    # the process prints is JSON. Its access log is turned off where the server is started:
    # it prints the client IP.
    logging.getLogger(SERVER_LOGGER_NAME).handlers = [handler]
    return logger
