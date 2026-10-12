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


# The compiled dashboard is served under this prefix (ADR 0016).
DASHBOARD_PREFIX = "/app"
DASHBOARD_MOUNT_NAME = "dashboard"
