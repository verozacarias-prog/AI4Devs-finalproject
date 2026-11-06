"""Whether an interpreted transfer can be registered without asking (domain rules, § 13; FEAT-006).

It can when everything is in sight: the amount, and on each side exactly one account of the
user, named by the same rule as the account of an expense (§ 1). The two accounts are distinct,
in the same currency, and already opened on its day. What is not in sight is not guessed: it is
asked in a pending (§ 5), and a reply adds to what was understood until nothing is missing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.domain.entities.account import Account, AccountType
from app.domain.entities.classification import Classification, RegistrationType
from app.domain.services.dates.local_date import local_today
from app.domain.services.transactions.account_resolution import (
    AccountWords,
    account_candidates,
    chosen_account,
    in_offer_order,
    named_or_mentioned,
    offered_accounts,
    verified_currency,
    verified_type,
)
from app.domain.services.transactions.movement_resolution import (
    ParsedKey,
    fits,
    movement_date,
    rounded,
    same_name,
    stored_amount,
)


class TransferField(StrEnum):
    """What a pending transfer may lack, by its field in TRANSFER, in the order it is asked."""

    AMOUNT = "amount"
    FROM_ACCOUNT = "from_account_id"
    TO_ACCOUNT = "to_account_id"


@dataclass(frozen=True)
class TransferSide:
    """One side of a transfer as far as it is known: the account, once the messages name only
    one, or the mention and the type that named several, to offer only those.
    """

    account: str | None = None
    mention: str | None = None
    type: AccountType | None = None


@dataclass(frozen=True)
class TransferInterpretation:
    """What is understood of one transfer, from its first message and the replies to it."""

    amount: Decimal | None
    origin: TransferSide
    destination: TransferSide
    transfer_date: date
    # The currency the messages say, as an ISO code.
    currency: str | None = None


@dataclass(frozen=True)
class ResolvedTransfer:
    """A transfer to register: the same amount leaves one account and reaches the other."""

    amount: Decimal
    from_account: Account
    to_account: Account
    transfer_date: date


@dataclass(frozen=True)
class MissingTransfer:
    """What the user has to say before it is registered, and what to offer for each side."""

    interpretation: TransferInterpretation
    fields: tuple[TransferField, ...]
    # What is already known, to name the pending.
    from_account: Account | None
    to_account: Account | None
    # For each side that is missing: the ones its mention named, or else all, without the
    # account of the other side.
    from_options: tuple[Account, ...]
    to_options: tuple[Account, ...]
    # Both sides named the same account: which mention is wrong is not known (CA-13).
    same_account: bool = False


@dataclass(frozen=True)
class TransferBeforeOpening:
    """A transfer dated before one of its accounts was opened: the origin if both (CA-15)."""

    account: Account
    opened_on: date


@dataclass(frozen=True)
class DifferentCurrencies:
    """A transfer between accounts of different currency: it needs a rate, not built yet."""


@dataclass(frozen=True)
class AnotherCurrencyThanItsAccounts:
    """A transfer in a currency the messages say that is not the one of an account it names:
    registering it in the one of the accounts would store another amount than the one said,
    and converting it needs a rate, not built yet (CA-14).
    """


TransferResolution = (
    ResolvedTransfer
    | MissingTransfer
    | TransferBeforeOpening
    | DifferentCurrencies
    | AnotherCurrencyThanItsAccounts
)


def is_transfer(classification: Classification) -> bool:
    return classification.registration_type is RegistrationType.TRANSFER


def interpret_transfer(
    classification: Classification, text: str, accounts: Sequence[Account], today: date
) -> TransferInterpretation:
    """What the first message of a transfer says, side by side (§ 1, CA-2)."""
    currency = verified_currency(classification, text)
    origin = _side(
        named_or_mentioned(
            text,
            AccountWords(
                classification.account,
                classification.account_type,
                classification.account_type_words,
                currency,
            ),
            accounts,
        )
    )
    destination = _side(
        named_or_mentioned(
            text,
            AccountWords(
                classification.to_account,
                classification.to_account_type,
                classification.to_account_type_words,
                currency,
            ),
            accounts,
        )
    )
    return TransferInterpretation(
        amount=classification.amount,
        origin=origin,
        destination=destination,
        transfer_date=movement_date(classification, today),
        currency=currency,
    )


def continue_transfer(
    previous: TransferInterpretation,
    classification: Classification,
    text: str,
    accounts: Sequence[Account],
) -> TransferInterpretation:
    """What a reply adds to the pending: what it says replaces what was understood."""
    currency = verified_currency(classification, text) or previous.currency
    origin = _continued_side(
        previous.origin,
        AccountWords(
            classification.account,
            classification.account_type,
            classification.account_type_words,
            currency,
        ),
        text,
        accounts,
        previous.destination,
    )
    destination = _continued_side(
        previous.destination,
        AccountWords(
            classification.to_account,
            classification.to_account_type,
            classification.to_account_type_words,
            currency,
        ),
        text,
        accounts,
        previous.origin,
    )
    return replace(
        previous,
        amount=classification.amount if classification.amount is not None else previous.amount,
        origin=origin,
        destination=destination,
        transfer_date=classification.transaction_date or previous.transfer_date,
        currency=currency,
    )


def transfer_corrections(previous: TransferInterpretation, current: TransferInterpretation) -> int:
    """How many fields that already had a value a reply changed (domain rules, § 5): the amount,
    the date, and the accounts, which count as one field however many of them changed. Completing
    a side that was missing, an amount that could not be stored, or choosing among the accounts
    offered for a side, does not count.
    """
    accounts_changed = any(
        before.account is not None and not same_name(before.account, after.account)
        for before, after in (
            (previous.origin, current.origin),
            (previous.destination, current.destination),
        )
    )
    amount_changed = (
        stored_amount(previous.amount) is not None and previous.amount != current.amount
    )
    date_changed = previous.transfer_date != current.transfer_date
    return sum((amount_changed, date_changed, accounts_changed))


def resolve_transfer(
    interpretation: TransferInterpretation,
    accounts: Sequence[Account],
    time_zone: str,
    primary_currency: str,
) -> TransferResolution:
    """The transfer to register, why it is not, or what the user has to say (§ 1, § 13).

    A transfer before one of its accounts was opened is never registered, whatever else it
    lacks: the answer is why (§ 2).
    """
    from_account = _by_name(accounts, interpretation.origin.account)
    to_account = _by_name(accounts, interpretation.destination.account)
    if from_account is not None and to_account is not None and from_account.id == to_account.id:
        # Which of the two mentions is wrong is not known: both are asked (CA-13).
        cleared = replace(interpretation, origin=TransferSide(), destination=TransferSide())
        return _missing(cleared, accounts, primary_currency, None, None, same_account=True)
    for account in (from_account, to_account):
        if account is not None:
            opened_on = local_today(account.opened_at, time_zone)
            if interpretation.transfer_date < opened_on:
                return TransferBeforeOpening(account=account, opened_on=opened_on)
    if (
        from_account is not None
        and to_account is not None
        and from_account.currency != to_account.currency
    ):
        return DifferentCurrencies()
    said = interpretation.currency
    if said is not None and any(
        account is not None and account.currency != said for account in (from_account, to_account)
    ):
        return AnotherCurrencyThanItsAccounts()
    amount = interpretation.amount
    if amount is None or not fits(amount) or from_account is None or to_account is None:
        return _missing(interpretation, accounts, primary_currency, from_account, to_account)
    return ResolvedTransfer(
        amount=rounded(amount),
        from_account=from_account,
        to_account=to_account,
        transfer_date=interpretation.transfer_date,
    )


def transfer_to_parsed_data(interpretation: TransferInterpretation) -> dict[str, str | None]:
    """What its pending keeps, as text: amounts never go through float."""
    amount = interpretation.amount
    origin, destination = interpretation.origin, interpretation.destination
    return {
        ParsedKey.TYPE: RegistrationType.TRANSFER,
        ParsedKey.AMOUNT: None if amount is None else str(amount),
        ParsedKey.CURRENCY: interpretation.currency,
        ParsedKey.ACCOUNT: origin.account,
        ParsedKey.ACCOUNT_MENTION: origin.mention,
        ParsedKey.ACCOUNT_TYPE: origin.type,
        ParsedKey.TO_ACCOUNT: destination.account,
        ParsedKey.TO_ACCOUNT_MENTION: destination.mention,
        ParsedKey.TO_ACCOUNT_TYPE: destination.type,
        ParsedKey.TRANSACTION_DATE: interpretation.transfer_date.isoformat(),
    }


def transfer_from_parsed_data(
    parsed: Mapping[str, str | None], today: date
) -> TransferInterpretation:
    """What a pending transfer kept, back as an interpretation."""
    kept_amount = parsed.get(ParsedKey.AMOUNT)
    kept_date = parsed.get(ParsedKey.TRANSACTION_DATE)
    return TransferInterpretation(
        amount=None if kept_amount is None else Decimal(kept_amount),
        origin=TransferSide(
            parsed.get(ParsedKey.ACCOUNT),
            parsed.get(ParsedKey.ACCOUNT_MENTION),
            _account_type(parsed.get(ParsedKey.ACCOUNT_TYPE)),
        ),
        destination=TransferSide(
            parsed.get(ParsedKey.TO_ACCOUNT),
            parsed.get(ParsedKey.TO_ACCOUNT_MENTION),
            _account_type(parsed.get(ParsedKey.TO_ACCOUNT_TYPE)),
        ),
        transfer_date=today if kept_date is None else date.fromisoformat(kept_date),
        currency=parsed.get(ParsedKey.CURRENCY),
    )


def registered(
    interpretation: TransferInterpretation, transfer: ResolvedTransfer
) -> TransferInterpretation:
    """What its pending keeps once registered: the accounts as they are stored."""
    return replace(
        interpretation,
        amount=transfer.amount,
        origin=TransferSide(transfer.from_account.name),
        destination=TransferSide(transfer.to_account.name),
        currency=transfer.from_account.currency,
    )


def _missing(
    interpretation: TransferInterpretation,
    accounts: Sequence[Account],
    primary_currency: str,
    from_account: Account | None,
    to_account: Account | None,
    *,
    same_account: bool = False,
) -> MissingTransfer:
    amount = interpretation.amount
    lacks = {
        TransferField.AMOUNT: amount is None or not fits(amount),
        TransferField.FROM_ACCOUNT: from_account is None,
        TransferField.TO_ACCOUNT: to_account is None,
    }
    return MissingTransfer(
        interpretation=interpretation,
        fields=tuple(field for field in TransferField if lacks[field]),
        from_account=from_account,
        to_account=to_account,
        # Each one only when its side is asked: the question says nothing else of them.
        from_options=()
        if from_account is not None
        else _options(interpretation.origin, accounts, to_account, primary_currency),
        to_options=()
        if to_account is not None
        else _options(interpretation.destination, accounts, from_account, primary_currency),
        same_account=same_account,
    )


def _options(
    side: TransferSide,
    accounts: Sequence[Account],
    other_side: Account | None,
    primary_currency: str,
) -> tuple[Account, ...]:
    """The ones its mention and its type named, or else all, without the account of the other
    side: offering is not choosing, so it is asked even when one is left. Decided by Vero on
    5/11/2026.
    """
    offered = offered_accounts(side.mention, side.type, accounts)
    return in_offer_order(
        [account for account in offered if other_side is None or account.id != other_side.id],
        primary_currency,
    )


def _side(named: tuple[str | None, str | None, AccountType | None]) -> TransferSide:
    account, mention, account_type = named
    return TransferSide(account, mention, account_type)


def _continued_side(
    side: TransferSide,
    said: AccountWords,
    text: str,
    accounts: Sequence[Account],
    other: TransferSide,
) -> TransferSide:
    """What a reply says of one side: the account it chooses among those offered, the mention
    that names several, or else what was understood. The currency alone chooses only on a side
    still missing.
    """
    names_an_account = said.mention is not None or (
        verified_type(said.type, said.type_words, text) is not None
    )
    if not names_an_account and (
        said.currency is None or side.account is not None or side.mention is None
    ):
        return side
    other_account = _by_name(accounts, other.account)
    offered = [
        account
        for account in offered_accounts(side.mention, side.type, accounts)
        if other_account is None or account.id != other_account.id
    ]
    chosen = chosen_account(text, said, accounts, offered)
    if chosen is not None:
        return TransferSide(chosen.name)
    if names_an_account and len(account_candidates(text, said, accounts)) > 1:
        # The reply names several: they are offered, and none is kept (CA-20).
        return TransferSide(None, said.mention, verified_type(said.type, said.type_words, text))
    return side


def _account_type(kept: str | None) -> AccountType | None:
    return None if kept is None else AccountType(kept)


def _by_name(accounts: Sequence[Account], name: str | None) -> Account | None:
    found = [account for account in accounts if name is not None and account.name == name]
    return found[0] if len(found) == 1 else None
