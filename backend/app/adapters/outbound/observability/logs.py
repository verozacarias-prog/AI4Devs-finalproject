"""JSON logs with a filter that lets through only what is known to be safe.

Rules (ADR 0023, docs/operacion.md 6.3):

- The message of a log record is its event name. Only a fixed name such as "http.request"
  passes; any other text, including text built from data, is redacted.
- Only the fields in ALLOWED_FIELDS pass, and only with a number, a boolean or a short token
  as value. Any other field or value is redacted, so a new field cannot leak by omission.
- Of an exception, only the class name is logged: its message and traceback can carry data.

Every logger of the process goes through the same handler, including the web server and the
libraries, because the handler is installed on the root logger.
"""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO

LOGGER_NAME = "platita"
REDACTED = "[redacted]"
ALLOWED_FIELDS = frozenset(
    {"message_id", "request_id", "user_id", "duration_ms", "result", "error_type"}
)

LogValue = str | int | float | bool | None

# Identifier of the API request being served. A request that is not a message gets one when
# it arrives; the worker will set the message id the same way.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_EVENT_NAME = re.compile(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+")
_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_RECORD_ATTRIBUTES = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
_HANDLER_NAME = "platita-json"
# The web server logs every access with the client IP; that log is turned off.
_SERVER_ACCESS_LOGGER = "uvicorn.access"
_SERVER_LOGGERS = ("uvicorn", "uvicorn.error")


def _extra_fields(record: logging.LogRecord) -> list[str]:
    return [name for name in record.__dict__ if name not in _RECORD_ATTRIBUTES]


def _is_safe_value(value: object) -> bool:
    if isinstance(value, str):
        return _TOKEN.fullmatch(value) is not None
    return isinstance(value, int | float | bool)


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for name in _extra_fields(record):
            value = record.__dict__[name]
            if value is None:
                continue
            if name not in ALLOWED_FIELDS or not _is_safe_value(value):
                record.__dict__[name] = REDACTED
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, version: str, process: str) -> None:
        super().__init__()
        self._version = version
        self._process = process

    def format(self, record: logging.LogRecord) -> str:
        event = record.getMessage()
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

    # However the server was started, its lines go to the root handler and nowhere else.
    for name in _SERVER_LOGGERS:
        server_logger = logging.getLogger(name)
        server_logger.handlers = []
        server_logger.propagate = True
        server_logger.setLevel(logging.INFO)
    access_logger = logging.getLogger(_SERVER_ACCESS_LOGGER)
    access_logger.handlers = []
    access_logger.disabled = True
