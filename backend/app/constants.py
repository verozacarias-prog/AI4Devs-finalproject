"""Names and default values shared by the whole process, in one place."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal


class Environment(StrEnum):
    """Where the process runs. Some features exist only in some environments (ADR 0016)."""

    LOCAL = "local"
    DEMO = "demo"
    PRODUCTION = "production"


class EnvVar(StrEnum):
    """The environment variables the process reads. `.env.example` lists the same names."""

    DATABASE_URL = "DATABASE_URL"
    MIGRATIONS_DATABASE_URL = "MIGRATIONS_DATABASE_URL"
    APPLICATION_DB_PASSWORD = "APPLICATION_DB_PASSWORD"  # noqa: S105
    APP_ENV = "APP_ENV"
    APP_VERSION = "APP_VERSION"
    DASHBOARD_DIR = "DASHBOARD_DIR"
    DEV_ENTRY_ENABLED = "DEV_ENTRY_ENABLED"
    WEB_CHAT_ENABLED = "WEB_CHAT_ENABLED"
    QUEUE_MAX_WAIT_MINUTES = "QUEUE_MAX_WAIT_MINUTES"
    WORKER_LOCK_SECONDS = "WORKER_LOCK_SECONDS"
    LLM_TIMEOUT_SECONDS = "LLM_TIMEOUT_SECONDS"
    MESSAGE_MAX_ATTEMPTS = "MESSAGE_MAX_ATTEMPTS"
    MESSAGE_RETRY_FIRST_WAIT_SECONDS = "MESSAGE_RETRY_FIRST_WAIT_SECONDS"
    MESSAGE_RETRY_MAX_WAIT_SECONDS = "MESSAGE_RETRY_MAX_WAIT_SECONDS"
    LLM_DAILY_CLASSIFICATION_LIMIT = "LLM_DAILY_CLASSIFICATION_LIMIT"
    LLM_DAILY_REGISTRATION_LIMIT = "LLM_DAILY_REGISTRATION_LIMIT"
    OPENAI_API_KEY = "OPENAI_API_KEY"


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

# The role the API and the worker log in with. The migrations create it and enable it (ADR 0030).
APPLICATION_ROLE = "platita_app"

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
# The retries of a message whose call to the model failed (ADR 0010, point 4): how many times
# it is tried, and how long it waits before each new attempt, growing by a factor up to a most.
# MESSAGE_MAX_ATTEMPTS and the two MESSAGE_RETRY_* variables change them.
DEFAULT_MESSAGE_MAX_ATTEMPTS = 3
DEFAULT_MESSAGE_RETRY_FIRST_WAIT_SECONDS = 30
DEFAULT_MESSAGE_RETRY_MAX_WAIT_SECONDS = 120
MESSAGE_RETRY_WAIT_GROWTH = 4

# The language model (ADR 0025). Prices are in dollars per million tokens, input and output, and
# give the estimated cost of each call when it is recorded (ADR 0023).
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-5.4-mini"
LLM_REASONING_EFFORT: Final[Literal["low"]] = "low"
# The most the model may write in one call, its reasoning included. An answer it cuts is a
# failed call, retried like any other (ADR 0010). The audit of 19/10/2026 asked for it (LLM10).
LLM_MAX_OUTPUT_TOKENS = 2000
LLM_PRICES_USD_PER_MILLION_TOKENS: dict[str, tuple[str, str]] = {"gpt-5.4-mini": ("0.75", "4.50")}
# Shorter than the lock of a message, so the call ends before another worker can take it: with
# a lock not longer than this, no process starts (ADR 0010). LLM_TIMEOUT_SECONDS changes it.
# Twenty seconds keeps the reply under the 30 of the p95 in docs/operacion.md.
DEFAULT_LLM_TIMEOUT_SECONDS = 20
# The daily limits of use of each user (domain rules, § 12): the messages classified a day,
# before classifying, and the registrations interpreted, after it. The two LLM_DAILY_*
# variables change them, without deploying (FEAT-003, CA-46).
DEFAULT_LLM_DAILY_CLASSIFICATION_LIMIT = 100
DEFAULT_LLM_DAILY_REGISTRATION_LIMIT = 50
# The worker retries a failed round itself (ADR 0010): the SDK does not retry on its own.
LLM_SDK_RETRIES = 0
TOKENS_PER_MILLION = 1_000_000

# The most a request and the web chat take (docs/04-api.md). The body fits the longest text
# even with every character escaped in JSON, at 12 bytes each.
MAX_REQUEST_BODY_BYTES = 64 * 1024
MAX_CHAT_TEXT_LENGTH = 4096
# How many messages the first read of the conversation brings, the latest ones.
CHAT_FIRST_READ_MESSAGES = 200

# The currencies a message can say, as the model returns them (domain rules, § 1).
MESSAGE_CURRENCIES = ("ARS", "USD")

# What a name the model proposes for a new category may be, checked in code before it is shown
# or stored (ADR 0013, point 10): letters, digits, spaces, hyphens, commas and brackets. With no
# dot, slash, colon or at sign, no link can pass.
CATEGORY_NAME_MAX_LENGTH = 40
CATEGORY_NAME_PATTERN = r"(?:[^\W_]|[ ,()-])+"

# How long a pending waits for its answer before it expires: the WhatsApp window for free text,
# so the reminder before it always fits (domain rules, § 5).
PENDING_VALIDITY_HOURS = 24

# What an operation command returns to the shell.
EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_FAILED = 2
