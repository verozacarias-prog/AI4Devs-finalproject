from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Budget:
    """The limit of one category in one period. A category without one has no limit."""

    id: uuid.UUID
    budget_period_id: uuid.UUID
    category_id: uuid.UUID
    limit_amount: Decimal
