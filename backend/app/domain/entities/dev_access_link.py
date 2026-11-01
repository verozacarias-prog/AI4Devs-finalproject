from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class DevAccessLink:
    """The personal link a person enters the demo environment with (ADR 0016).

    It holds the HMAC of its value, never the value. It has no user until the person accepts
    the test notice.
    """

    id: uuid.UUID
    label: str
    user_id: uuid.UUID | None
    token_hash: str


def hash_link_value(value: str, server_key: str) -> str:
    return hmac.new(server_key.encode(), value.encode(), hashlib.sha256).hexdigest()
