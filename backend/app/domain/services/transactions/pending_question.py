"""The question of a pending: what was understood, and what the user has to say (§ 5; FEAT-003).

The first line says the movement as far as it is known; then one line for each thing that is
missing, in the order of MissingField, with what can be chosen.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app import messages
from app.constants import LINE_END
from app.domain.entities.transaction import TransactionType
from app.domain.services.transactions.movement_resolution import Missing, MissingField
from app.domain.services.transactions.registration_confirmation import (
    written_amount,
    written_day,
)

_MOVEMENT = {
    TransactionType.EXPENSE: messages.QUESTION_EXPENSE,
    TransactionType.INCOME: messages.QUESTION_INCOME,
}


def question_text(
    missing: Missing, currency: str, limits: Sequence[tuple[str, Decimal]] = ()
) -> str:
    """`currency` is the one its amount is in; `limits`, those of the draft, by category."""
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
    first = (
        messages.QUESTION_ONE_MISSING
        if len(missing.fields) == 1
        else messages.QUESTION_SEVERAL_MISSING
    )
    lines = [first.format(movement=movement)]
    lines.extend(_line(field, missing, limits) for field in missing.fields)
    return LINE_END.join(lines)


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
