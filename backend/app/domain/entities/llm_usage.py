from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.constants import (
    DEFAULT_LLM_DAILY_CLASSIFICATION_LIMIT,
    DEFAULT_LLM_DAILY_REGISTRATION_LIMIT,
)


class UsageCounter(StrEnum):
    """A daily counter of a user in LLM_USAGE (domain rules, § 12).

    `classification` is the total daily cap: it counts every message classified, before its
    class is known, and is no quota of its own. `registration` is the quota of registration.
    """

    CLASSIFICATION = "classification"
    REGISTRATION = "registration"


@dataclass(frozen=True)
class UsageLimits:
    """How many of each counter a user may use a day. They are configuration (CA-46)."""

    classification: int = DEFAULT_LLM_DAILY_CLASSIFICATION_LIMIT
    registration: int = DEFAULT_LLM_DAILY_REGISTRATION_LIMIT

    def of(self, counter: UsageCounter) -> int:
        if counter is UsageCounter.CLASSIFICATION:
            return self.classification
        return self.registration
