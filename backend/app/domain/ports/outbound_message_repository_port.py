from __future__ import annotations

from typing import Protocol

from app.domain.entities.outbound_message import OutboundMessage


class OutboundMessageRepositoryPort(Protocol):
    def add(self, message: OutboundMessage) -> None: ...
