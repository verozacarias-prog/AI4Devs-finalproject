"""An expense or an income, in AnswerMessage: registered, asked, continued or discarded
(FEAT-003).
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from decimal import Decimal

from app import messages
from app.domain.entities.budget_period import PeriodStatus
from app.domain.entities.category import Category
from app.domain.entities.classification import (
    Classification,
    PendingReply,
)
from app.domain.entities.outbound_message import ResponseKind
from app.domain.entities.pending_transaction import (
    BatchStatus,
    PendingBatch,
    PendingIntent,
    PendingStatus,
    PendingTransaction,
)
from app.domain.entities.transaction import Transaction, TransactionSource, TransactionType
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.transactions.movement_resolution import (
    BeforeAccountOpening,
    Interpretation,
    Missing,
    MissingField,
    NotYetSupported,
    ResolvedMovement,
    continue_interpretation,
    corrections,
    from_parsed_data,
    proposes_an_unwritten_name,
    resolve,
    same_name,
    to_parsed_data,
)
from app.domain.services.transactions.pending_question import (
    question_text,
)
from app.domain.services.transactions.registration_confirmation import (
    before_opening_text,
    confirmation_text,
)
from app.domain.use_cases.messages.reply_context import (
    ReplyContext,
    add_reply,
    ask_in_pending,
    close_pending,
    closed_batch,
    fixed_text,
    new_pending,
    reject,
)


def continue_movement(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    awaiting: tuple[PendingBatch, PendingTransaction],
    classification: Classification,
) -> bool:
    """A message while a pending expense or income awaits its reply (domain rules, § 5). True
    if it completed or discarded it: it uses the quota of registration (§ 12).
    """
    batch, pending = awaiting
    match classification.pending_reply:
        case PendingReply.DISCARDS:
            close_pending(unit_of_work, awaiting, PendingStatus.REJECTED, context.user.id)
            add_reply(unit_of_work, context, messages.PENDING_DISCARDED, ResponseKind.FIXED_TEXT)
            return True
        case PendingReply.CONTINUES:
            interpretation, corrected = continued_movement(
                unit_of_work, context, pending, classification
            )
            return settle_movement(unit_of_work, context, interpretation, (batch, corrected))
        case PendingReply.OTHER_MOVEMENT | None:
            # Not about the pending: it keeps waiting, and the message gets its fixed text.
            # Another movement joins the batch before it gets here (FEAT-007, CA-13).
            add_reply(unit_of_work, context, fixed_text(classification), ResponseKind.FIXED_TEXT)
            return False


def continued_movement(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    pending: PendingTransaction,
    classification: Classification,
) -> tuple[Interpretation, PendingTransaction]:
    """What a reply makes of a pending expense or income: what it adds or changes, a yes to what
    its question offered, and the pending with the corrections counted (domain rules, § 5).
    """
    previous = from_parsed_data(pending.parsed_data, context.today)
    interpretation = continue_interpretation(
        previous, classification, context.message.text, context.accounts
    )
    # Counted before a yes fills what was missing, which is not a correction.
    corrected = replace(
        pending,
        corrected_fields_count=pending.corrected_fields_count
        + corrections(previous, interpretation),
    )
    # A yes to a name nobody offered nor wrote accepts nothing: it is asked again.
    if classification.accepts_proposal and not proposes_an_unwritten_name(
        previous, classification, context.message.text
    ):
        interpretation = _accept_proposal(unit_of_work, context, pending, previous, interpretation)
    return interpretation, corrected


def _accept_proposal(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    pending: PendingTransaction,
    asked: Interpretation,
    interpretation: Interpretation,
) -> Interpretation:
    """A yes to what the question offered: the category to create, or the draft to confirm.

    The draft is the one the question showed, for the day it asked about, and only while the
    movement still falls in it: a yes never confirms a period the user did not see (§ 3).
    """
    proposed = interpretation.proposed_category
    if (
        MissingField.CATEGORY in pending.missing_fields
        and proposed is not None
        and interpretation.type is not None
    ):
        category = _category_named(unit_of_work, context, proposed, interpretation.type)
        interpretation = replace(interpretation, category=category.name)
    if MissingField.PERIOD in pending.missing_fields:
        shown = unit_of_work.budget_periods.list_covering(context.user.id, asked.transaction_date)
        if (
            len(shown) == 1
            and shown[0].status is PeriodStatus.DRAFT
            and shown[0].user_id == context.user.id
            and shown[0].period_start <= interpretation.transaction_date <= shown[0].period_end
        ):
            unit_of_work.budget_periods.confirm(shown[0].id)
    return interpretation


def _category_named(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, name: str, kind: TransactionType
) -> Category:
    """The category the user confirmed: the one with that name if there is one, or a new one.

    A category of the user never repeats a name of the base catalog (domain rules, § 4).
    """
    existing = [
        category
        for category in context.categories
        if category.kind is kind and same_name(category.name, name)
    ]
    if existing:
        return existing[0]
    created = Category(id=uuid.uuid4(), name=name.strip(), kind=kind, user_id=context.user.id)
    unit_of_work.categories.add(created)
    context.categories.append(created)
    return created


def settle_movement(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    interpretation: Interpretation,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> bool:
    """Registers it, says why not, or asks what is missing, in a new pending or in the open one.

    False when it cannot be registered yet, whatever it says (§ 12, C3-24).
    """
    resolution = resolve_movement(unit_of_work, context, interpretation)
    match resolution:
        case ResolvedMovement():
            _register(unit_of_work, context, resolution, interpretation, awaiting)
        case BeforeAccountOpening():
            text = before_opening_text(
                resolution.type, resolution.account.name, resolution.opened_on
            )
            reject(unit_of_work, context, awaiting, text)
        case NotYetSupported(several_periods=True):
            reject(unit_of_work, context, awaiting, messages.SEVERAL_PERIODS)
        case NotYetSupported():
            reject(unit_of_work, context, awaiting, messages.CANNOT_REGISTER_YET)
        case Missing():
            _ask(unit_of_work, context, resolution, awaiting)
    return not isinstance(resolution, NotYetSupported)


def resolve_movement(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, interpretation: Interpretation
) -> Missing | ResolvedMovement | BeforeAccountOpening | NotYetSupported:
    periods = unit_of_work.budget_periods.list_covering(
        context.user.id, interpretation.transaction_date
    )
    return resolve(
        interpretation,
        context.accounts,
        context.categories,
        periods,
        context.user.time_zone,
        context.user.primary_currency,
    )


def _ask(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    missing: Missing,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> None:
    """The question, and the pending that keeps what was understood (§ 5)."""
    # Only the currency the messages said: the one of an account was never said (CA-48).
    ask_in_pending(
        unit_of_work,
        context,
        movement_question(unit_of_work, context, missing),
        to_parsed_data(missing.interpretation, missing.interpretation.currency),
        tuple(field.value for field in missing.fields),
        PendingIntent.TRANSACTION,
        awaiting,
    )


def amount_currency(context: ReplyContext, missing: Missing) -> str:
    """The currency its amount is in: the one of its account, or else the primary one."""
    return context.user.primary_currency if missing.account is None else missing.account.currency


def movement_question(unit_of_work: UnitOfWorkPort, context: ReplyContext, missing: Missing) -> str:
    limits: list[tuple[str, Decimal]] = []
    if missing.draft is not None:
        names = {category.id: category.name for category in context.categories}
        limits = sorted(
            (names[budget.category_id], budget.limit_amount)
            for budget in unit_of_work.budgets.list_by_period(missing.draft.id)
            if budget.category_id in names
        )
    return question_text(missing, limits)


def movement_missing_of(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, pending: PendingTransaction
) -> Missing:
    """What an open pending lacks, as it was asked: from what it kept, the same way."""
    interpretation = from_parsed_data(pending.parsed_data, context.today)
    resolution = resolve_movement(unit_of_work, context, interpretation)
    if not isinstance(resolution, Missing):
        # Something changed since it was asked, as a period that now exists: the question is
        # the one its missing fields say.
        resolution = Missing(
            interpretation=interpretation,
            fields=tuple(MissingField(field) for field in pending.missing_fields),
            account=None,
            category=None,
            account_options=(),
            draft=None,
        )
    return resolution


def _register(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    movement: ResolvedMovement,
    interpretation: Interpretation,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> None:
    """The movement and its confirmation. Its pending is promoted and its batch closed, the open
    one or a new batch of one (domain rules, § 5): the batch keeps the confirmation, so quoting
    it later finds the movement.
    """
    user_id = context.user.id
    transaction = new_transaction(context, movement)
    unit_of_work.transactions.add(transaction)
    confirmation = add_reply(
        unit_of_work,
        context,
        movement_confirmation(unit_of_work, movement, None),
        ResponseKind.REGISTRATION,
    )
    parsed = registered_parsed_data(movement, interpretation)
    if awaiting is not None:
        batch, pending = awaiting
        unit_of_work.pendings.update(
            replace(
                pending,
                parsed_data=parsed,
                missing_fields=(),
                resulting_transaction_id=transaction.id,
                status=PendingStatus.PROMOTED,
                resolved_by=user_id,
            )
        )
        unit_of_work.pendings.update_batch(
            replace(
                batch,
                awaiting_reply=False,
                confirmation_message_id=confirmation.id,
                status=BatchStatus.CLOSED,
            )
        )
        return
    batch = closed_batch(context, confirmation)
    unit_of_work.pendings.add_batch(batch)
    unit_of_work.pendings.add(
        new_pending(context, batch, parsed, (), PendingStatus.PROMOTED, transaction.id, user_id)
    )


def new_transaction(context: ReplyContext, movement: ResolvedMovement) -> Transaction:
    return Transaction(
        id=uuid.uuid4(),
        user_id=context.user.id,
        account_id=movement.account.id,
        type=movement.type,
        amount=movement.amount,
        currency=movement.account.currency,
        exchange_rate=None,
        transaction_date=movement.transaction_date,
        budget_period_id=movement.period.id,
        category_id=movement.category.id,
        source=TransactionSource.MANUAL,
    )


def movement_confirmation(
    unit_of_work: UnitOfWorkPort, movement: ResolvedMovement, position: int | None
) -> str:
    """What its confirmation says of it: alone, or with its number in a batch of several."""
    group_id = movement.period.family_group_id
    group = None if group_id is None else unit_of_work.family_groups.find_by_id(group_id)
    return confirmation_text(
        type=movement.type,
        amount=movement.amount,
        currency=movement.account.currency,
        account_name=movement.account.name,
        category_name=movement.category.name,
        transaction_date=movement.transaction_date,
        period=movement.period,
        group_name=None if group is None else group.name,
        position=position,
    )


def registered_parsed_data(
    movement: ResolvedMovement, interpretation: Interpretation
) -> dict[str, str | None]:
    """What its pending keeps once promoted: the names of the account and the category."""
    return to_parsed_data(
        replace(interpretation, account=movement.account.name, category=movement.category.name),
        movement.account.currency,
    )
