"""The names that appear in a log line, in one place (docs/operacion.md 6.3).

An event name is always one of these constants, never text built at the call site: that is
what keeps data out of the message of a log record.
"""

from __future__ import annotations

from enum import StrEnum

# What replaces anything the filter does not let through.
REDACTED = "[redacted]"

# The shape each part of a log line must have to pass the filter.
EVENT_NAME_PATTERN = r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+"
IDENTIFIER_PATTERN = r"[0-9a-f]{32}|[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}"
CLASS_NAME_PATTERN = r"[A-Za-z_][A-Za-z0-9_]{0,63}"
SHORT_WORD_PATTERN = r"[a-z][a-z_]{0,31}"
MAX_EVENT_LENGTH = 64
MAX_DURATION_MS = 3_600_000
MIN_RESULT_CODE = 100
MAX_RESULT_CODE = 599

HANDLER_NAME = "platita-json"


class Event(StrEnum):
    HTTP_REQUEST = "http.request"
    DATABASE_UNREACHABLE = "database.unreachable"


class Field(StrEnum):
    """The only fields a log line may carry. Each one has its rule in logs.FIELD_RULES."""

    MESSAGE_ID = "message_id"
    REQUEST_ID = "request_id"
    USER_ID = "user_id"
    DURATION_MS = "duration_ms"
    RESULT = "result"
    ERROR_TYPE = "error_type"


class LineKey(StrEnum):
    """The keys every log line has, written by the formatter itself."""

    TIMESTAMP = "ts"
    LEVEL = "level"
    PROCESS = "process"
    VERSION = "version"
    LOGGER = "logger"
    EVENT = "event"


class LoggerName(StrEnum):
    APP = "platita"
    API = "platita.api"
    POSTGRES = "platita.postgres"
    # Third-party loggers the process reconfigures.
    SERVER = "uvicorn"
    SERVER_ERROR = "uvicorn.error"
    SERVER_ACCESS = "uvicorn.access"
