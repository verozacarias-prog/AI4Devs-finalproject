from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OnboardingStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True)
class User:
    """A person who uses the assistant. The row exists only once the terms were accepted."""

    id: uuid.UUID
    name: str
    whatsapp_phone: str
    country: str
    # IANA name. "Today" for this user is always computed in this zone.
    time_zone: str
    primary_currency: str
    exchange_rate_reference: str | None
    terms_accepted_at: datetime
    terms_version: str
    notifications_opt_in: bool
    onboarding_status: OnboardingStatus
