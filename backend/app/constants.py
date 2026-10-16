"""Names and default values shared by the whole process, in one place."""

from __future__ import annotations

from enum import StrEnum


class Environment(StrEnum):
    """Where the process runs. Some features exist only in some environments (ADR 0016)."""

    LOCAL = "local"
    DEMO = "demo"
    PRODUCTION = "production"


class EnvVar(StrEnum):
    """The environment variables the process reads. `.env.example` lists the same names."""

    DATABASE_URL = "DATABASE_URL"
    APP_ENV = "APP_ENV"
    APP_VERSION = "APP_VERSION"
    DASHBOARD_DIR = "DASHBOARD_DIR"
    DEV_ENTRY_ENABLED = "DEV_ENTRY_ENABLED"
    WEB_CHAT_ENABLED = "WEB_CHAT_ENABLED"
    QUEUE_MAX_WAIT_MINUTES = "QUEUE_MAX_WAIT_MINUTES"
    WORKER_LOCK_SECONDS = "WORKER_LOCK_SECONDS"


class ProcessName(StrEnum):
    """The processes that share the image. Each log line says which one wrote it."""

    API = "api"
    OPERATOR_COMMAND = "operator_command"
    WORKER = "worker"


# How a variable that turns something on or off is written. Nothing else is accepted.
ENABLED = "true"
DISABLED = "false"

APP_TITLE = "Platita"

DEFAULT_VERSION = "dev"

# For code that builds the application without ever touching the database, such as the
# command that exports the API contract.
UNUSED_DATABASE_URL = "postgresql+psycopg://unused@localhost/unused"
# The environment has no default (docs/operacion.md, section 2). This one is for that same
# code, which serves nobody.
CONTRACT_EXPORT_ENVIRONMENT = Environment.LOCAL
DATABASE_CONNECT_TIMEOUT_SECONDS = 3

# Layout of the compiled dashboard, as the build tool leaves it.
DASHBOARD_INDEX_FILE = "index.html"
DASHBOARD_ASSETS_FOLDER = "assets"

MILLISECONDS_PER_SECOND = 1000

# A path whose last segment contains this names a file, not a route of the dashboard.
FILE_EXTENSION_SEPARATOR = "."
# How a list of allowed values is written inside a message.
LIST_SEPARATOR = ", "
# Layout of the exported API contract. Stable, so the pipeline can compare files.
JSON_INDENT = 2
LINE_END = "\n"

# Where the API listens inside its container. Compose publishes it on localhost only.
API_HOST = "0.0.0.0"  # noqa: S104
API_PORT = 8000

# The message worker (ADR 0010). The lock is how long a message stays taken by one worker: if
# the worker falls, the message is free again when it ends; WORKER_LOCK_SECONDS changes it.
# The pause is how long it waits before asking again when there was nothing to take.
DEFAULT_WORKER_LOCK_SECONDS = 120
# A quarter of a second keeps the reply of a fixed text under a second, and at this volume
# four reads a second of an indexed table cost nothing.
WORKER_IDLE_SECONDS = 0.25
# How long a pending message may wait before GET /queuez fails (docs/04-api.md), unless
# QUEUE_MAX_WAIT_MINUTES says otherwise.
DEFAULT_QUEUE_MAX_WAIT_MINUTES = 10

# What an operation command returns to the shell.
EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_FAILED = 2
