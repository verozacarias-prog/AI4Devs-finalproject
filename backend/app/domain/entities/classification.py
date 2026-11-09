from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.domain.entities.account import AccountType


class MessageClass(StrEnum):
    """What a message asks for: the first thing the model decides (ADR 0018)."""

    REGISTRATION = "registration"
    QUERY = "query"
    ADVICE = "advice"
    # A greeting, or anything the model cannot place: it gets a request for details.
    NONE = "none"


class RegistrationType(StrEnum):
    """What a registration wants to register. An expense, an income and a transfer have code."""

    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"
    CARD_PURCHASE = "card_purchase"
    RECURRING_RULE = "recurring_rule"
    # A correction, a deletion or a restoration of a movement already confirmed.
    CHANGE = "change"


class PendingReply(StrEnum):
    """What a message does to the batch that awaits a reply (domain rules, § 5)."""

    # It answers the question: what it adds or changes of each pending goes by its number.
    CONTINUES = "continues"
    # It brings another movement instead.
    OTHER_MOVEMENT = "other_movement"
    # The user does not want any of them registered.
    DISCARDS = "discards"


@dataclass(frozen=True)
class NumberedPending:
    """One pending of the batch a message may answer: the memory of a registration (ADR 0018,
    point 9). Its number in the batch, what was understood and what is missing, by field name.
    Never an identifier.
    """

    number: int
    interpreted: Mapping[str, str | None]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class OpenBatch:
    """The batch a message may answer, with every pending it still asks about, and the
    question the user got (domain rules, § 5). A single pending is a batch of one.
    """

    pendings: tuple[NumberedPending, ...]
    question: str


@dataclass(frozen=True)
class ClassificationRequest:
    """What the model gets to classify a message: the task data and no identifier (ADR 0013)."""

    text: str
    accounts: tuple[str, ...]
    expense_categories: tuple[str, ...]
    income_categories: tuple[str, ...]
    # The day the user wrote, in their time zone: what "today" and "ayer" mean.
    today: date
    # The batch awaiting a reply of the user, if any.
    open_batch: OpenBatch | None = None


@dataclass(frozen=True)
class ModelUsage:
    """What a call to the model cost, as the provider reports it. It never holds content."""

    provider: str
    model: str
    prompt_version: str
    # None when the provider did not report them.
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class MovementReading:
    """One movement of a message, as the model read it. Names are as the model wrote them.

    The fields mean the same as those of a classification with one movement (FEAT-007, CA-1).
    """

    registration_type: RegistrationType | None = None
    amount: Decimal | None = None
    account: str | None = None
    account_type: AccountType | None = None
    account_type_words: str | None = None
    to_account: str | None = None
    to_account_type: AccountType | None = None
    to_account_type_words: str | None = None
    category: str | None = None
    currency: str | None = None
    currency_words: str | None = None
    transaction_date: date | None = None
    proposed_category: str | None = None


@dataclass(frozen=True)
class NumberedReply:
    """What a reply says of one pending of the batch, by its number (FEAT-007, CA-9).

    `reading` has only what the reply adds or changes. `discards` drops that pending, and
    `accepts_proposal` is a yes to what its question offered, as creating the category or
    confirming the draft.
    """

    number: int
    reading: MovementReading = MovementReading()
    discards: bool = False
    accepts_proposal: bool = False


@dataclass(frozen=True)
class Classification:
    """What the model understood of a message. Names are as the model wrote them.

    The fields of a movement are those of its first movement, or its only one; the ones after
    it, in the order the message writes them, are in `more_movements` (FEAT-007).
    """

    message_class: MessageClass
    registration_type: RegistrationType | None = None
    amount: Decimal | None = None
    # How the message names the account, in its own words: the code decides which it is. In a
    # transfer, the account the money leaves.
    account: str | None = None
    # The type of account the message says, and the words that say it: the code checks them.
    account_type: AccountType | None = None
    account_type_words: str | None = None
    # In a transfer, the account the money goes to, said the same way as the other one.
    to_account: str | None = None
    to_account_type: AccountType | None = None
    to_account_type_words: str | None = None
    category: str | None = None
    # Only when the message says it, as "pesos", "lucas" or "dólares": an ISO code.
    currency: str | None = None
    # The words that say the currency, as the message writes them: the code checks them.
    currency_words: str | None = None
    # Only when the message says which day; otherwise it is the day the user wrote.
    transaction_date: date | None = None
    # A name for a new category, when none of the user fits.
    proposed_category: str | None = None
    # The movements after the first, when the message has more than one.
    more_movements: tuple[MovementReading, ...] = ()
    # Only while a batch awaits a reply: what the message does to it, and, when it answers,
    # what it says of each pending by its number.
    pending_reply: PendingReply | None = None
    numbered_replies: tuple[NumberedReply, ...] = ()
    # In the reply to one pending, from `for_pending`: a yes to what its question offered.
    accepts_proposal: bool = False
    usage: ModelUsage | None = None
    # The row the call left in LLM_CALL, once the wrapper recorded it (ADR 0023).
    call_id: uuid.UUID | None = None

    def movements(self) -> tuple[MovementReading, ...]:
        """Every movement of the message, the first one included, in the order it writes them."""
        first = MovementReading(
            registration_type=self.registration_type,
            amount=self.amount,
            account=self.account,
            account_type=self.account_type,
            account_type_words=self.account_type_words,
            to_account=self.to_account,
            to_account_type=self.to_account_type,
            to_account_type_words=self.to_account_type_words,
            category=self.category,
            currency=self.currency,
            currency_words=self.currency_words,
            transaction_date=self.transaction_date,
            proposed_category=self.proposed_category,
        )
        return (first, *self.more_movements)

    def brought_movements(self) -> tuple[MovementReading, ...]:
        """The movements a reply to the open batch also brings: those with an amount. A reply
        that brings none may still leave a type or a currency in those fields (FEAT-007, CA-22).
        """
        return tuple(movement for movement in self.movements() if movement.amount is not None)

    def of_movement(self, movement: MovementReading) -> Classification:
        """This classification with only that movement, to resolve it as if it came alone."""
        return replace(
            self,
            registration_type=movement.registration_type,
            amount=movement.amount,
            account=movement.account,
            account_type=movement.account_type,
            account_type_words=movement.account_type_words,
            to_account=movement.to_account,
            to_account_type=movement.to_account_type,
            to_account_type_words=movement.to_account_type_words,
            category=movement.category,
            currency=movement.currency,
            currency_words=movement.currency_words,
            transaction_date=movement.transaction_date,
            proposed_category=movement.proposed_category,
            more_movements=(),
        )

    def for_pending(self, number: int) -> Classification:
        """This reply as it concerns the pending with that number: its fields are what the
        reply says of it, and nothing when it says nothing of it. Dropping it is `DISCARDS`.
        A message that does not answer the batch, as another movement, stays as it is.
        """
        if self.pending_reply is not PendingReply.CONTINUES:
            return self
        reply = next(
            (reply for reply in self.numbered_replies if reply.number == number),
            NumberedReply(number=number),
        )
        pending_reply = PendingReply.DISCARDS if reply.discards else PendingReply.CONTINUES
        return replace(
            self.of_movement(reply.reading),
            pending_reply=pending_reply,
            numbered_replies=(),
            accepts_proposal=reply.accepts_proposal,
        )
