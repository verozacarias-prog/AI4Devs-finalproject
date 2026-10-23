"""Case C2-12 of FEAT-001 (docs/features/FEAT-001/spec.md): without an exchange rate, the
balance is not computed, rather than adding dollars as if they were pesos."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.entities.account import Account, AccountType
from app.domain.entities.transaction import Transaction, TransactionType
from app.domain.errors import InconsistentDataError
from app.domain.services.accounts.account_balance import balance_of


def test_without_an_exchange_rate_the_balance_is_not_computed() -> None:
    # Case C2-12: 50 dollars on an account in pesos, with no rate.
    galicia = Account(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Galicia pesos",
        type=AccountType.BANK_ACCOUNT,
        currency="ARS",
        initial_balance=Decimal("350000.00"),
        opened_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    )
    expense = Transaction(
        id=uuid.uuid4(),
        user_id=galicia.user_id,
        account_id=galicia.id,
        type=TransactionType.EXPENSE,
        amount=Decimal("50.00"),
        currency="USD",
        exchange_rate=None,
        transaction_date=date(2026, 10, 10),
    )

    with pytest.raises(InconsistentDataError):
        balance_of(galicia, [expense], [], date(2026, 10, 15))
