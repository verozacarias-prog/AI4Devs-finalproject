from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class AccountType(StrEnum):
    BANK_ACCOUNT = "bank_account"
    DIGITAL_WALLET = "digital_wallet"
    BROKER = "broker"
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    RECEIVABLE = "receivable"


class BalanceKind(StrEnum):
    """What the number of an account is: its balance, or what was put in an investment."""

    BALANCE = "balance"
    # An investment account: what was declared on opening, plus transfers in, minus out.
    NET_CONTRIBUTED = "net_contributed"


@dataclass(frozen=True)
class Account:
    """An account of a user. Its balance is never stored: it is computed from its movements."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    type: AccountType
    currency: str
    # The balance on the day the account was opened; nothing is registered before that day.
    initial_balance: Decimal
    opened_at: datetime
