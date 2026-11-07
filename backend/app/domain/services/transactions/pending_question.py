"""The question of a pending: what the user has to say (§ 5; FEAT-003).

One line for each thing that is missing, in the order of MissingField, with what can be chosen,
after a line that says why when the amount given does not fit where it is stored. It does not
repeat what was understood (CA-22): only the list of a batch of several names each pending, by
its number (FEAT-007, CA-8).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app import messages
from app.constants import LINE_END, SENTENCE_SEPARATOR
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
# The fixed texts that may follow a colon: they go on the sentence in lower case.
_FIXED_STARTS = (
    messages.CANNOT_REGISTER_YET,
    messages.SEVERAL_PERIODS,
    messages.TRANSFER_IN_DIFFERENT_CURRENCIES,
    messages.TRANSFER_IN_ANOTHER_CURRENCY,
)


def question_text(missing: Missing, limits: Sequence[tuple[str, Decimal]] = ()) -> str:
    """`limits` are those of the draft, by category."""
    lines = [_line(field, missing, limits) for field in missing.fields]
    amount = missing.interpretation.amount
    if amount is not None and too_large(amount):
        # Why the amount it gave is asked again, before the question (domain rules, § 5).
        lines.insert(0, messages.AMOUNT_TOO_LARGE)
    return LINE_END.join(lines)


def movement_description(missing: Missing, currency: str) -> str:
    """A pending as far as it is known: "el gasto de $3.500 en Supermercado". `currency` is the
    one its amount is in.
    """
    interpretation = missing.interpretation
    amount = interpretation.amount
    return _movement(
        interpretation.type,
        None if MissingField.AMOUNT in missing.fields else amount,
        currency,
        None if missing.category is None else missing.category.name,
        None if missing.account is None else missing.account.name,
    )


def complete_movement_description(
    type: TransactionType, amount: Decimal, currency: str, category: str, account: str
) -> str:
    """A pending that lacks nothing: "el gasto de $3.500 en Supermercado con Mercado Pago"."""
    return _movement(type, amount, currency, category, account)


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


def transfer_description(missing: MissingTransfer, currency: str) -> str:
    """A pending transfer as far as it is known: "la transferencia de US$100"."""
    amount = missing.interpretation.amount
    return _transfer(
        None if TransferField.AMOUNT in missing.fields else amount,
        currency,
        None if missing.from_account is None else missing.from_account.name,
        None if missing.to_account is None else missing.to_account.name,
    )


def complete_transfer_description(
    amount: Decimal, currency: str, from_account: str, to_account: str
) -> str:
    """A transfer that lacks nothing: "la transferencia de $20.000 de Galicia pesos a MP"."""
    return _transfer(amount, currency, from_account, to_account)


def batch_item_text(position: int, description: str, question: str | None) -> str:
    """One pending of the list, by its number: what was understood, and its question, or that
    it is complete (FEAT-007, CA-8).
    """
    movement = description[:1].upper() + description[1:]
    if question is None:
        return messages.BATCH_ITEM_COMPLETE.format(position=position, movement=movement)
    return LINE_END.join(
        (messages.BATCH_ITEM.format(position=position, movement=movement), question)
    )


def batch_list_text(items: Sequence[str]) -> str:
    """The pendings of the batch, a blank line between one and the next."""
    return (LINE_END * 2).join(items)


def not_registered_by_order(index: int, reason: str) -> str:
    """A movement of the message that does not enter the batch, by its order (CA-12)."""
    return messages.NOT_REGISTERED_BY_ORDER.format(
        ordinal=messages.ORDINALS[index], reason=_continued(reason)
    )


def not_registered_by_number(position: int, reason: str) -> str:
    """A pending a reply left unable to be registered, by its number (CA-12)."""
    return messages.NOT_REGISTERED_BY_NUMBER.format(position=position, reason=_continued(reason))


def message_overflow_text(taken: int, left: int) -> str:
    """What a message with more movements than fit in a batch says it took (CA-14)."""
    others = (
        messages.OTHER_IN_ANOTHER_MESSAGE
        if left == 1
        else messages.OTHERS_IN_ANOTHER_MESSAGE.format(left=left)
    )
    return SENTENCE_SEPARATOR.join(
        (messages.TOOK_THE_FIRST_OF_THE_MESSAGE.format(taken=taken), others)
    )


def new_movements_overflow_text(taken: int, left: int) -> str:
    """What a message that fills the open batch says it took of its movements (CA-14)."""
    if taken == 0:
        return messages.TOOK_NONE_OF_THE_NEW
    took = (
        messages.TOOK_THE_FIRST_NEW
        if taken == 1
        else messages.TOOK_THE_FIRST_NEW_ONES.format(taken=taken)
    )
    others = (
        messages.OTHER_WHEN_WE_FINISH
        if left == 1
        else messages.OTHERS_WHEN_WE_FINISH.format(left=left)
    )
    return SENTENCE_SEPARATOR.join((took, others))


def _continued(text: str) -> str:
    """A fixed text after a colon: it goes on the sentence, so its first word is not capital.

    A text that starts with the name of an account keeps it as the user wrote it.
    """
    return text if not text.startswith(_FIXED_STARTS) else text[:1].lower() + text[1:]


def _transfer(
    amount: Decimal | None, currency: str, from_account: str | None, to_account: str | None
) -> str:
    transfer = messages.QUESTION_TRANSFER
    if amount is not None:
        transfer += messages.QUESTION_AMOUNT_PART.format(amount=written_amount(amount, currency))
    if from_account is not None:
        transfer += messages.QUESTION_FROM_ACCOUNT_PART.format(account=from_account)
    if to_account is not None:
        transfer += messages.QUESTION_TO_ACCOUNT_PART.format(account=to_account)
    return transfer


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


def _movement(
    type: TransactionType | None,
    amount: Decimal | None,
    currency: str,
    category: str | None,
    account: str | None,
) -> str:
    movement = messages.QUESTION_MOVEMENT if type is None else _MOVEMENT[type]
    if amount is not None:
        movement += messages.QUESTION_AMOUNT_PART.format(amount=written_amount(amount, currency))
    if category is not None:
        movement += messages.QUESTION_CATEGORY_PART.format(category=category)
    if account is not None:
        movement += messages.QUESTION_ACCOUNT_PART.format(account=account)
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
