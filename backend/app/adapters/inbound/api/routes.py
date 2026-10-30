"""The paths of the API, in one place. The contract is in docs/04-api.md."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

HEALTHZ = "/healthz"
READYZ = "/readyz"
QUEUEZ = "/queuez"
HEALTH_TAG = "health"


class HealthState(StrEnum):
    """The only two answers of a health route."""

    OK = "ok"
    UNAVAILABLE = "unavailable"


# The session (docs/04-api.md). The cookie is the same for the login by code and for the
# development entry. Its prefix makes the browser reject it without Secure and Path=/.
ME = "/me"
AUTH_LOGOUT = "/auth/logout"
SESSION_TAG = "session"
SESSION_COOKIE = "__Host-sid"
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_SAME_SITE: Literal["strict"] = "strict"

# The accounts of the user of the session, with their computed balance.
ACCOUNTS = "/accounts"
ACCOUNTS_TAG = "accounts"

# Reading the budget: the periods, the summary of one, and one limit with its movements.
BUDGET_PERIODS = "/budget-periods"
BUDGET_PERIOD = "/budget-periods/{period_id}"
BUDGET_PERIOD_CONFIRM = "/budget-periods/{period_id}/confirm"
BUDGET_PERIOD_SUMMARY = "/budget-periods/{period_id}/summary"
BUDGET = "/budgets/{budget_id}"
BUDGETS_TAG = "budgets"

# The categories of expenses a limit can go on.
CATEGORIES = "/categories"
CATEGORIES_TAG = "categories"

# The web chat. It exists only when it is enabled, and never in production (ADR 0016).
CHAT_MESSAGES = "/chat/messages"
CHAT_TAG = "chat"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"

# The development entry. It exists only when it is enabled, and never in production.
DEV_USERS = "/dev/users"
DEV_SESSION = "/dev/session"
DEV_TAG = "dev"

# A request that changes something must come from the page of the API itself, as JSON.
ORIGIN_HEADER = "origin"
HOST_HEADER = "host"
CONTENT_TYPE_HEADER = "content-type"
JSON_CONTENT_TYPE = "application/json"
MEDIA_TYPE_PARAMETER_SEPARATOR = ";"
READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Every response says which request it answers, under this header (docs/04-api.md).
REQUEST_ID_HEADER = "X-Request-Id"
# The one field every error body has: its code.
ERROR_KEY = "error"


class ApiErrorCode(StrEnum):
    """The codes the API answers on its own, when no use case raised the error."""

    INVALID_REQUEST = "invalid_request"
    INTERNAL_ERROR = "internal_error"


# The compiled dashboard is served under this prefix (ADR 0016).
DASHBOARD_PREFIX = "/app"
DASHBOARD_MOUNT_NAME = "dashboard"
