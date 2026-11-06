"""The question of a pending: what the user has to say (§ 5; FEAT-003).

One line for each thing that is missing, in the order of MissingField, with what can be chosen,
after a line that says why when the amount given does not fit where it is stored. It does not
repeat what was understood (CA-22): only the text that repeats it for another movement names
the pending (CA-36).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app import messages
from app.constants import LINE_END
from app.domain.entities.transaction import TransactionType
from app.domain.services.transactions.movement_resolution import (
    Missing,
    MissingField,
    too_large,
)
from app.domain.services.transactions.registration_confirmation import (
    written_amount,
    written_day,
)
from app.domain.services.transactions.transfer_resolution import (
    MissingTransfer,
    TransferField,
)

_MOVEMENT = {
    TransactionType.EXPENSE: messages.QUESTION_EXPENSE,
    TransactionType.INCOME: messages.QUESTION_INCOME,
}


def question_text(missing: Missing, limits: Sequence[tuple[str, Decimal]] = ()) -> str:
    """`limits` are those of the draft, by category."""
    lines = [_line(field, missing, limits) for field in missing.fields]
    amount = missing.interpretation.amount
    if amount is not None and too_large(amount):
        # Why the amount it gave is asked again, before the question (domain rules, § 5).
        lines.insert(0, messages.AMOUNT_TOO_LARGE)
    return LINE_END.join(lines)


def finish_the_pending_first_text(missing: Missing, currency: str) -> str:
    """What precedes its question when another movement comes: it names the pending (CA-36).

    `currency` is the one its amount is in.
    """
    return messages.FINISH_THE_PENDING_FIRST.format(movement=_movement(missing, currency))


def transfer_question_text(missing: MissingTransfer) -> str:
    """One line for each thing a transfer lacks, after the one that says why both accounts are
    asked when they were the same (CA-13), or why the amount is asked again (§ 5).
    """
    lines = [_transfer_line(field, missing) for field in missing.fields]
    if missing.same_account:
        lines.insert(0, messages.SAME_ACCOUNT_ON_BOTH_SIDES)
    amount = missing.interpretation.amount
    if amount is not None and too_large(amount):
        lines.insert(0, messages.AMOUNT_TOO_LARGE)
    return LINE_END.join(lines)


def finish_the_transfer_first_text(missing: MissingTransfer, currency: str) -> str:
    """What precedes its question when another movement comes: it names the pending transfer,
    as "la transferencia de $20.000 de Galicia pesos" (CA-36 of FEAT-003).
    """
    transfer = messages.QUESTION_TRANSFER
    amount = missing.interpretation.amount
    if amount is not None and TransferField.AMOUNT not in missing.fields:
        transfer += messages.QUESTION_AMOUNT_PART.format(amount=written_amount(amount, currency))
    if missing.from_account is not None:
        transfer += messages.QUESTION_FROM_ACCOUNT_PART.format(account=missing.from_account.name)
    if missing.to_account is not None:
        transfer += messages.QUESTION_TO_ACCOUNT_PART.format(account=missing.to_account.name)
    return messages.FINISH_THE_PENDING_FIRST.format(movement=transfer)


def _transfer_line(field: TransferField, missing: MissingTransfer) -> str:
    match field:
        case TransferField.AMOUNT:
            return messages.ASK_AMOUNT
        case TransferField.FROM_ACCOUNT:
            names = [account.name for account in missing.from_options]
            return messages.ASK_FROM_ACCOUNT.format(options=_options(names))
        case TransferField.TO_ACCOUNT:
            names = [account.name for account in missing.to_options]
            return messages.ASK_TO_ACCOUNT.format(options=_options(names))


def _movement(missing: Missing, currency: str) -> str:
    """The pending as far as it is known: "el gasto de $3.500 en Supermercado"."""
    interpretation = missing.interpretation
    movement = (
        messages.QUESTION_MOVEMENT
        if interpretation.type is None
        else _MOVEMENT[interpretation.type]
    )
    if interpretation.amount is not None and MissingField.AMOUNT not in missing.fields:
        movement += messages.QUESTION_AMOUNT_PART.format(
            amount=written_amount(interpretation.amount, currency)
        )
    if missing.category is not None:
        movement += messages.QUESTION_CATEGORY_PART.format(category=missing.category.name)
    if missing.account is not None:
        movement += messages.QUESTION_ACCOUNT_PART.format(account=missing.account.name)
    return movement


def _line(field: MissingField, missing: Missing, limits: Sequence[tuple[str, Decimal]]) -> str:
    match field:
        case MissingField.TYPE:
            return messages.ASK_TYPE
        case MissingField.AMOUNT:
            return messages.ASK_AMOUNT
        case MissingField.ACCOUNT:
            names = [account.name for account in missing.account_options]
            return messages.ASK_ACCOUNT.format(options=_options(names))
        case MissingField.CATEGORY:
            if missing.existing_category is not None:
                return messages.OFFER_EXISTING_CATEGORY.format(
                    category=missing.existing_category.name
                )
            proposed = missing.interpretation.proposed_category
            if proposed is None:
                return messages.ASK_CATEGORY
            return messages.PROPOSE_CATEGORY.format(category=proposed)
        case MissingField.PERIOD:
            return _period_line(missing, limits)


def _period_line(missing: Missing, limits: Sequence[tuple[str, Decimal]]) -> str:
    draft = missing.draft
    if draft is None:
        return messages.NO_PERIOD.format(date=written_day(missing.interpretation.transaction_date))
    currency = draft.primary_currency
    if limits:
        written_limits = messages.DRAFT_LIMITS.format(
            limits=messages.OPTION_SEPARATOR.join(
                messages.DRAFT_LIMIT.format(category=name, amount=written_amount(amount, currency))
                for name, amount in limits
            )
        )
    else:
        written_limits = messages.DRAFT_WITHOUT_LIMITS
    return messages.CONFIRM_DRAFT.format(
        start=written_day(draft.period_start),
        end=written_day(draft.period_end),
        income=written_amount(draft.estimated_income, currency),
        limits=written_limits,
    )


def _options(names: Sequence[str]) -> str:
    """ "A, B, C o D": the last two joined by "o". There is always one at least."""
    if len(names) == 1:
        return names[0]
    return messages.OPTION_SEPARATOR.join(names[:-1]) + messages.LAST_OPTION_JOINER + names[-1]
