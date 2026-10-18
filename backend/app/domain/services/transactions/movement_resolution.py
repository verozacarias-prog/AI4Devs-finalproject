"""Whether an interpreted expense or income can be registered without asking (domain rules, § 1).

It can when everything is in sight: the type, the amount, one account of the user by its name,
one of the categories of its kind, and one possible period for its day, already confirmed. What
is missing is asked in a pending (§ 5), and a reply adds to what was understood until nothing
is missing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.constants import CATEGORY_NAME_MAX_LENGTH, CATEGORY_NAME_PATTERN
from app.domain.entities.account import Account, AccountType
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus
from app.domain.entities.category import Category
from app.domain.entities.classification import Classification, RegistrationType
from app.domain.entities.transaction import TransactionType
from app.domain.services.dates.local_date import local_today
from app.domain.services.transactions.account_resolution import (
    account_candidates,
    is_written,
)

_TRANSACTION_TYPES = {
    RegistrationType.EXPENSE: TransactionType.EXPENSE,
    RegistrationType.INCOME: TransactionType.INCOME,
}
# Where an expense or an income can be registered. A card purchase is another registration
# type, and an investment account moves only by transfers.
_ACCOUNT_TYPES_FOR_MOVEMENTS = (
    AccountType.BANK_ACCOUNT,
    AccountType.DIGITAL_WALLET,
    AccountType.CASH,
)
# Two decimals, as the database stores an amount (docs/03-modelo-de-datos.md).
_CENTS = Decimal("0.01")
_CATEGORY_NAME = re.compile(CATEGORY_NAME_PATTERN)


class MissingField(StrEnum):
    """What a pending may lack, by the name of its field, in the order it is asked (§ 5)."""

    TYPE = "type"
    AMOUNT = "amount"
    ACCOUNT = "account_id"
    CATEGORY = "category_id"
    PERIOD = "budget_period_id"


class ParsedKey(StrEnum):
    """The keys of what a pending keeps of what was understood, as text."""

    TYPE = "type"
    AMOUNT = "amount"
    CURRENCY = "currency"
    ACCOUNT = "account"
    # The words of an account that named several: only those are offered.
    ACCOUNT_MENTION = "account_mention"
    CATEGORY = "category"
    PROPOSED_CATEGORY = "proposed_category"
    TRANSACTION_DATE = "transaction_date"


@dataclass(frozen=True)
class Interpretation:
    """What is understood of one movement, from its first message and the replies to it.

    Names as the user's accounts and categories have them, or as the model wrote them.
    """

    type: TransactionType | None
    amount: Decimal | None
    # The account, once the messages name only one.
    account: str | None
    account_mention: str | None
    category: str | None
    proposed_category: str | None
    transaction_date: date


@dataclass(frozen=True)
class ResolvedMovement:
    type: TransactionType
    amount: Decimal
    account: Account
    category: Category
    period: BudgetPeriod
    transaction_date: date


@dataclass(frozen=True)
class BeforeAccountOpening:
    """A movement dated before its account was opened: it is already in the initial balance."""

    type: TransactionType
    account: Account
    opened_on: date


@dataclass(frozen=True)
class Missing:
    """What the user has to say before it is registered, and what to offer for each thing."""

    interpretation: Interpretation
    fields: tuple[MissingField, ...]
    # What is already known, to say it in the question.
    account: Account | None
    category: Category | None
    # When the account is missing: the ones the messages named, or else all.
    account_options: tuple[Account, ...]
    # When the period is missing: its only draft, to confirm it; None when there is no period.
    draft: BudgetPeriod | None
    # When the category is missing and the one proposed already exists by that name: it is
    # offered instead of creating another (domain rules, § 4).
    existing_category: Category | None = None


@dataclass(frozen=True)
class NotYetSupported:
    """What delivery 2 does not register: another currency than its period, or more than one
    possible period, which belong to the final delivery.
    """


Resolution = ResolvedMovement | BeforeAccountOpening | Missing | NotYetSupported


def movement_date(classification: Classification, today: date) -> date:
    """The day the message says, or else the day the user wrote."""
    return classification.transaction_date or today


def is_movement(classification: Classification) -> bool:
    """A registration of an expense or an income, or one that does not say which of the two."""
    return classification.registration_type is None or (
        classification.registration_type in _TRANSACTION_TYPES
    )


def interpret(
    classification: Classification, text: str, accounts: Sequence[Account], today: date
) -> Interpretation:
    """What the first message of a movement says."""
    account, mention = _named(text, classification, _movement_accounts(accounts))
    return Interpretation(
        type=_TRANSACTION_TYPES.get(classification.registration_type)
        if classification.registration_type is not None
        else None,
        amount=classification.amount,
        account=account,
        account_mention=mention,
        category=classification.category,
        proposed_category=_valid_proposal(classification.proposed_category),
        transaction_date=movement_date(classification, today),
    )


def continue_interpretation(
    previous: Interpretation,
    classification: Classification,
    text: str,
    accounts: Sequence[Account],
) -> Interpretation:
    """What a reply adds to the pending: what it says replaces what was understood."""
    movement_accounts = _movement_accounts(accounts)
    account, mention = previous.account, previous.account_mention
    currency = verified_currency(classification, text)
    if classification.account is not None or (currency is not None and mention is not None):
        offered = (
            account_candidates(mention, mention, None, movement_accounts)
            if mention is not None
            else movement_accounts
        )
        chosen = _chosen(text, classification.account, currency, movement_accounts, offered)
        if chosen is not None:
            account, mention = chosen.name, None
    registration_type = classification.registration_type
    return replace(
        previous,
        type=_TRANSACTION_TYPES.get(registration_type, previous.type)
        if registration_type is not None
        else previous.type,
        amount=classification.amount if classification.amount is not None else previous.amount,
        account=account,
        account_mention=mention,
        category=classification.category or previous.category,
        proposed_category=_written_proposal(classification, text) or previous.proposed_category,
        transaction_date=classification.transaction_date or previous.transaction_date,
    )


def corrections(previous: Interpretation, current: Interpretation) -> int:
    """How many fields already interpreted a reply changed: completing a missing one does not
    count (domain rules, § 5). The currency goes with the account, so it counts with it.
    """
    kept = (
        (previous.type, current.type),
        (previous.amount, current.amount),
        (previous.transaction_date, current.transaction_date),
        (previous.category, current.category),
        (previous.account, current.account),
    )
    return sum(1 for before, after in kept if before is not None and not _same(before, after))


def _same(before: object, after: object) -> bool:
    """Names are the same whatever their case, as the code recognizes them."""
    if isinstance(before, str) and isinstance(after, str):
        return same_name(before, after)
    return before == after


def resolve(
    interpretation: Interpretation,
    accounts: Sequence[Account],
    categories: Sequence[Category],
    periods: Sequence[BudgetPeriod],
    time_zone: str,
    primary_currency: str,
) -> Resolution:
    """The movement to register, why it is not, or what the user has to say (§ 1).

    A movement before its account was opened is never registered, whatever else it lacks: the
    answer is why (§ 2). `periods` are the ones that cover its day, which the use case reads
    before: a domain service touches no port.
    """
    movement_accounts = _movement_accounts(accounts)
    account = _by_name(movement_accounts, interpretation.account)
    if account is not None and interpretation.type is not None:
        opened_on = local_today(account.opened_at, time_zone)
        if interpretation.transaction_date < opened_on:
            return BeforeAccountOpening(
                type=interpretation.type, account=account, opened_on=opened_on
            )
    if _not_yet_supported(account, periods):
        return NotYetSupported()
    period = periods[0] if periods else None
    category = _category_of(interpretation, categories)
    missing = _missing_fields(interpretation, account, category, period)
    if missing:
        return Missing(
            interpretation=interpretation,
            fields=missing,
            account=account,
            category=category,
            # Each one only when its field is asked: the question says nothing else of them.
            account_options=_options(interpretation, movement_accounts, primary_currency)
            if MissingField.ACCOUNT in missing
            else (),
            draft=period,
            existing_category=_named_category(
                categories, interpretation.type, interpretation.proposed_category
            )
            if MissingField.CATEGORY in missing
            else None,
        )
    assert interpretation.type is not None and interpretation.amount is not None
    assert account is not None and category is not None and period is not None
    return ResolvedMovement(
        type=interpretation.type,
        amount=rounded(interpretation.amount),
        account=account,
        category=category,
        period=period,
        transaction_date=interpretation.transaction_date,
    )


def _not_yet_supported(account: Account | None, periods: Sequence[BudgetPeriod]) -> bool:
    """What belongs to the final delivery, whatever else the movement lacks."""
    if len(periods) > 1:
        # Choosing between the budget of the user and that of a group.
        return True
    if not periods:
        return False
    period = periods[0]
    # A draft of a group waits for its owner (§ 3), and another currency than the period needs
    # a rate, which is not built yet.
    return (period.status is PeriodStatus.DRAFT and period.user_id is None) or (
        account is not None and period.primary_currency != account.currency
    )


def _missing_fields(
    interpretation: Interpretation,
    account: Account | None,
    category: Category | None,
    period: BudgetPeriod | None,
) -> tuple[MissingField, ...]:
    """What the user has to say, in the order it is asked (§ 5)."""
    lacks = {
        MissingField.TYPE: interpretation.type is None,
        MissingField.AMOUNT: interpretation.amount is None or rounded(interpretation.amount) <= 0,
        MissingField.ACCOUNT: account is None,
        MissingField.CATEGORY: interpretation.type is not None and category is None,
        MissingField.PERIOD: period is None or period.status is not PeriodStatus.CONFIRMED,
    }
    return tuple(field for field in MissingField if lacks[field])


def verified_currency(classification: Classification, text: str) -> str | None:
    """The currency the message says: none if the words the model gave are not in it (CA-39).

    Without words, the currency counts as the model gave it: Vero decided so on 17/10/2026.
    """
    words = classification.currency_words
    if words is not None and not is_written(words, text):
        return None
    return classification.currency


def rounded(amount: Decimal) -> Decimal:
    """To two decimals, half up, before it is stored (docs/03-modelo-de-datos.md)."""
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


def to_parsed_data(interpretation: Interpretation, currency: str | None) -> dict[str, str | None]:
    """What a pending keeps, as text: amounts never go through float."""
    return {
        ParsedKey.TYPE: interpretation.type,
        ParsedKey.AMOUNT: None if interpretation.amount is None else str(interpretation.amount),
        ParsedKey.CURRENCY: currency,
        ParsedKey.ACCOUNT: interpretation.account,
        ParsedKey.ACCOUNT_MENTION: interpretation.account_mention,
        ParsedKey.CATEGORY: interpretation.category,
        ParsedKey.PROPOSED_CATEGORY: interpretation.proposed_category,
        ParsedKey.TRANSACTION_DATE: interpretation.transaction_date.isoformat(),
    }


def from_parsed_data(parsed: Mapping[str, str | None], today: date) -> Interpretation:
    """What a pending kept, back as an interpretation."""
    kept_type = parsed.get(ParsedKey.TYPE)
    kept_amount = parsed.get(ParsedKey.AMOUNT)
    kept_date = parsed.get(ParsedKey.TRANSACTION_DATE)
    return Interpretation(
        type=None if kept_type is None else TransactionType(kept_type),
        amount=None if kept_amount is None else Decimal(kept_amount),
        account=parsed.get(ParsedKey.ACCOUNT),
        account_mention=parsed.get(ParsedKey.ACCOUNT_MENTION),
        category=parsed.get(ParsedKey.CATEGORY),
        proposed_category=parsed.get(ParsedKey.PROPOSED_CATEGORY),
        transaction_date=today if kept_date is None else date.fromisoformat(kept_date),
    )


def proposes_an_unwritten_name(
    previous: Interpretation, classification: Classification, text: str
) -> bool:
    """Whether a reply comes with a name for the category that the question did not offer and
    the reply does not write: a yes to it creates nothing (CA-45, ADR 0028).
    """
    proposed = _valid_proposal(classification.proposed_category)
    return (
        proposed is not None
        and not same_name(proposed, previous.proposed_category)
        and not is_written(proposed, text)
    )


def rejects_output(
    classification: Classification, text: str, previous: Interpretation | None
) -> bool:
    """Whether the checks in code drop something the model returned (ADR 0023, CA-47).

    A mention of the account or words of the currency the message does not write (CA-9,
    CA-39), a name of category that does not pass its check (CA-43), and, in a reply to a
    pending, a name nobody offered nor wrote (CA-45). What is dropped is never used: this only
    says it happened, for the metric of hallucinations.
    """
    account = classification.account
    words = classification.currency_words
    proposed = classification.proposed_category
    return (
        (account is not None and not is_written(account, text))
        or (words is not None and not is_written(words, text))
        or (proposed is not None and _valid_proposal(proposed) is None)
        or (previous is not None and proposes_an_unwritten_name(previous, classification, text))
    )


def _written_proposal(classification: Classification, text: str) -> str | None:
    """In a reply, a new name counts only if the reply writes it, as "llamala Barbería"."""
    proposed = _valid_proposal(classification.proposed_category)
    return proposed if proposed is not None and is_written(proposed, text) else None


def _valid_proposal(name: str | None) -> str | None:
    """The name the model proposes, if it passes the check in code; otherwise none (CA-43)."""
    if name is None:
        return None
    stripped = name.strip()
    if len(stripped) > CATEGORY_NAME_MAX_LENGTH or not _CATEGORY_NAME.fullmatch(stripped):
        return None
    return stripped


def same_name(stored: str, written: str | None) -> bool:
    return written is not None and stored.casefold() == written.strip().casefold()


def _named(
    text: str, classification: Classification, accounts: Sequence[Account]
) -> tuple[str | None, str | None]:
    """The account the message names, or the mention that named several of them."""
    candidates = account_candidates(
        text, classification.account, verified_currency(classification, text), accounts
    )
    if len(candidates) == 1:
        return candidates[0].name, None
    if len(candidates) > 1:
        return None, classification.account
    return None, None


def _chosen(
    text: str,
    mention: str | None,
    currency: str | None,
    accounts: Sequence[Account],
    offered: Sequence[Account],
) -> Account | None:
    """The account a reply chooses: by its name, or by its currency among those offered."""
    named = account_candidates(text, mention, currency, accounts)
    if len(named) == 1:
        return named[0]
    offered_ids = {account.id for account in offered}
    among_offered = [account for account in named if account.id in offered_ids]
    if len(among_offered) == 1:
        return among_offered[0]
    if currency is not None:
        in_currency = [account for account in offered if account.currency == currency]
        if len(in_currency) == 1:
            return in_currency[0]
    return None


def _options(
    interpretation: Interpretation, accounts: Sequence[Account], primary_currency: str
) -> tuple[Account, ...]:
    """The ones the mention named, or else all: first those in the primary currency of the
    user, and within each currency the bank, the wallet and the cash, so the order never
    changes.
    """
    mention = interpretation.account_mention
    offered = list(accounts)
    if mention is not None:
        named = account_candidates(mention, mention, None, accounts)
        if len(named) > 1:
            offered = named
    return tuple(
        sorted(
            offered,
            key=lambda account: (
                account.currency != primary_currency,
                _ACCOUNT_TYPES_FOR_MOVEMENTS.index(account.type),
                account.name,
            ),
        )
    )


def _movement_accounts(accounts: Sequence[Account]) -> list[Account]:
    """Those an expense or an income can go to."""
    return [account for account in accounts if account.type in _ACCOUNT_TYPES_FOR_MOVEMENTS]


def _category_of(interpretation: Interpretation, categories: Sequence[Category]) -> Category | None:
    return _named_category(categories, interpretation.type, interpretation.category)


def _named_category(
    categories: Sequence[Category], kind: TransactionType | None, name: str | None
) -> Category | None:
    if kind is None:
        return None
    found = [
        category
        for category in categories
        if category.kind is kind and same_name(category.name, name)
    ]
    return found[0] if len(found) == 1 else None


def _by_name(accounts: Sequence[Account], name: str | None) -> Account | None:
    found = [account for account in accounts if name is not None and account.name == name]
    return found[0] if len(found) == 1 else None
