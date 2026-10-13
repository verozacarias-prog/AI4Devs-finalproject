from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.domain.entities.session import Session


class SessionRepositoryPort(Protocol):
    def add(self, session: Session) -> None: ...

    def find_by_token_hash(self, token_hash: str) -> Session | None: ...

    def touch(self, session_id: uuid.UUID, at: datetime) -> None:
        """Records activity: the idle limit counts from here."""
        ...

    def revoke(self, session_id: uuid.UUID, at: datetime) -> None: ...
