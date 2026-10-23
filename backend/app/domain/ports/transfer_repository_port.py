from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.transfer import Transfer


class TransferRepositoryPort(Protocol):
    def list_by_user(self, user_id: uuid.UUID) -> list[Transfer]:
        """Every transfer of the user, deleted ones included."""
        ...
