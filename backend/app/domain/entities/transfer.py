from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Transfer:
    """Money moved between two accounts of the same user. It is in no budget.

    Each side is in the currency of its own account, so neither needs converting.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    from_account_id: uuid.UUID
    from_amount: Decimal
    from_currency: str
    to_account_id: uuid.UUID
    to_amount: Decimal
    to_currency: str
    exchange_rate: Decimal | None
    transfer_date: date
    deleted_at: datetime | None = None
