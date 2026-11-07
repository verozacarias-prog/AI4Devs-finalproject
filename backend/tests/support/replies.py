"""What the model answers to a message that answers the open batch, for the doubles of the tests.

A single pending is a batch of one (FEAT-007): what the reply says of it goes by its number, 1.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.entities.account import AccountType
from app.domain.entities.classification import (
    Classification,
    MessageClass,
    MovementReading,
    NumberedReply,
    PendingReply,
    RegistrationType,
)


def reply_to_pending(
    *,
    number: int = 1,
    registration_type: RegistrationType | None = None,
    amount: Decimal | None = None,
    account: str | None = None,
    account_type: AccountType | None = None,
    account_type_words: str | None = None,
    to_account: str | None = None,
    to_account_type: AccountType | None = None,
    to_account_type_words: str | None = None,
    category: str | None = None,
    currency: str | None = None,
    currency_words: str | None = None,
    transaction_date: date | None = None,
    proposed_category: str | None = None,
    accepts_proposal: bool = False,
) -> Classification:
    """A reply that answers the pending with that number, adding or changing those fields."""
    return Classification(
        MessageClass.REGISTRATION,
        pending_reply=PendingReply.CONTINUES,
        numbered_replies=(
            NumberedReply(
                number=number,
                reading=MovementReading(
                    registration_type=registration_type,
                    amount=amount,
                    account=account,
                    account_type=account_type,
                    account_type_words=account_type_words,
                    to_account=to_account,
                    to_account_type=to_account_type,
                    to_account_type_words=to_account_type_words,
                    category=category,
                    currency=currency,
                    currency_words=currency_words,
                    transaction_date=transaction_date,
                    proposed_category=proposed_category,
                ),
                accepts_proposal=accepts_proposal,
            ),
        ),
    )
