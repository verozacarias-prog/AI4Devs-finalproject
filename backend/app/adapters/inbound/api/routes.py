"""The paths of the API, in one place. The contract is in docs/04-api.md."""

from __future__ import annotations

from enum import StrEnum

HEALTHZ = "/healthz"
READYZ = "/readyz"
HEALTH_TAG = "health"


class HealthState(StrEnum):
    """The only two answers of a health route."""

    OK = "ok"
    UNAVAILABLE = "unavailable"


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
