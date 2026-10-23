from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

# A session ends twelve hours after it was opened, or after thirty minutes without activity,
# whichever comes first (ADR 0016).
SESSION_LIFETIME = timedelta(hours=12)
SESSION_IDLE_LIMIT = timedelta(minutes=30)
# 256 bits of randomness.
TOKEN_BYTES = 32


@dataclass(frozen=True)
class Session:
    """An open session of the dashboard. It holds the hash of its token, never the token."""

    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None

    def is_valid_at(self, now: datetime) -> bool:
        return (
            self.revoked_at is None
            and now < self.expires_at
            and now - self.last_seen_at < SESSION_IDLE_LIMIT
        )


def new_token() -> str:
    """The random value that travels in the cookie. Every session gets a new one."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    # The token is random and long, so a plain hash is enough: there is nothing to guess.
    return hashlib.sha256(token.encode()).hexdigest()


def open_session(user_id: uuid.UUID, token: str, now: datetime) -> Session:
    return Session(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=hash_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=now + SESSION_LIFETIME,
        revoked_at=None,
    )
