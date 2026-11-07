"""A batch of several movements, in AnswerMessage (FEAT-007): registered together when all of
them are complete, or listed by number with what each one lacks, answered by number, and joined
by the movements of a later message.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from app import messages
from app.constants import BATCH_MAX_PENDINGS, LINE_END
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
from app.domain.entities.transaction import Transaction
from app.domain.entities.transfer import Transfer
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.transactions.movement_resolution import (
    BeforeAccountOpening,
    Interpretation,
    Missing,
    NotYetSupported,
    ResolvedMovement,
    from_parsed_data,
    interpret,
    is_movement,
    to_parsed_data,
)
from app.domain.services.transactions.pending_question import (
    batch_item_text,
    batch_list_text,
    complete_movement_description,
    complete_transfer_description,
    message_overflow_text,
    movement_description,
    new_movements_overflow_text,
    not_registered_by_number,
    not_registered_by_order,
    transfer_description,
    transfer_question_text,
)
from app.domain.services.transactions.registration_confirmation import (
    batch_confirmation_text,
    before_opening_text,
    transfer_before_opening_text,
)
from app.domain.services.transactions.transfer_resolution import (
    AnotherCurrencyThanItsAccounts,
    DifferentCurrencies,
    MissingTransfer,
    ResolvedTransfer,
    TransferBeforeOpening,
    TransferInterpretation,
    interpret_transfer,
    is_transfer,
    registered,
    transfer_from_parsed_data,
    transfer_to_parsed_data,
)
from app.domain.use_cases.messages.movement_registration import (
    amount_currency,
    continued_movement,
    movement_confirmation,
    movement_question,
    new_transaction,
    registered_parsed_data,
    resolve_movement,
)
from app.domain.use_cases.messages.reply_context import (
    FIRST_POSITION,
    ReplyContext,
    add_reply,
    close_batch,
    closed_batch,
    fixed_text,
    new_pending,
    open_batch,
)
from app.domain.use_cases.messages.transfer_registration import (
    continued_transfer,
    new_transfer,
    resolve_user_transfer,
    transfer_confirmation,
    transfer_currency,
)


@dataclass(frozen=True)
class _MovementToRegister:
    """An expense or an income of a batch, resolved, with what the messages said of it."""

    movement: ResolvedMovement
    interpretation: Interpretation


@dataclass(frozen=True)
class _TransferToRegister:
    """A transfer of a batch, resolved, with what the messages said of it."""

    transfer: ResolvedTransfer
    interpretation: TransferInterpretation


@dataclass(frozen=True)
class _CannotEnter:
    """A movement that cannot be registered yet, and the fixed text that says why (CA-12)."""

    reason: str


# What a movement of the batch is: complete, or lacking something the list asks.
_State = _MovementToRegister | _TransferToRegister | Missing | MissingTransfer


@dataclass(frozen=True)
class _Item:
    """A pending of the batch, by its number: the stored one, or None while it is new.

    `answered` says whether this message changed it, so that only those are stored again.
    """

    position: int
    state: _State
    pending: PendingTransaction | None
    answered: bool = False


def answer_several(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, classification: Classification
) -> bool:
    """A message with several movements (FEAT-007). Each one is resolved as if it came alone:
    complete, they are registered together; with something missing, none is, and the list asks
    for it (CA-8). What cannot be registered yet stays out, in a line of its own (CA-12), and
    beyond 10 the rest waits for another message (CA-14).

    True if some movement entered the batch: it uses the quota of registration (§ 12).
    """
    movements = list(map(classification.of_movement, classification.movements()))
    taken = movements[:BATCH_MAX_PENDINGS]
    items: list[_Item] = []
    notes: list[str] = []
    for index, single in enumerate(taken):
        state = _new_state(unit_of_work, context, single)
        if isinstance(state, _CannotEnter):
            notes.append(not_registered_by_order(index, state.reason))
        else:
            items.append(_Item(FIRST_POSITION + len(items), state, None))
    left = len(movements) - len(taken)
    overflow = message_overflow_text(len(taken), left) if left else None
    _settle(unit_of_work, context, None, items, notes, overflow)
    return bool(items)


def join_batch(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    batch: PendingBatch,
    in_batch: Sequence[PendingTransaction],
    classification: Classification,
) -> bool:
    """Another movement while the batch awaits a reply: it joins with the next number, and the
    list goes again, up to date (CA-13). Only those that fit in 10 join (CA-14).

    True if some movement joined: it uses the quota of registration (§ 12).
    """
    items, notes = _open_items(unit_of_work, context, in_batch)
    last = max(pending.position for pending in in_batch)
    movements = list(map(classification.of_movement, classification.movements()))
    taken = movements[: BATCH_MAX_PENDINGS - last]
    joined = 0
    for index, single in enumerate(taken):
        state = _new_state(unit_of_work, context, single)
        if isinstance(state, _CannotEnter):
            notes.append(not_registered_by_order(index, state.reason))
        else:
            joined += 1
            items.append(_Item(last + joined, state, None))
    left = len(movements) - len(taken)
    overflow = new_movements_overflow_text(len(taken), left) if left else None
    _settle(unit_of_work, context, batch, items, notes, overflow)
    return joined > 0


def continue_batch(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    batch: PendingBatch,
    in_batch: Sequence[PendingTransaction],
    classification: Classification,
) -> bool:
    """A message while a batch of several awaits its reply (CA-9 to CA-12). What it says of
    each pending goes by its number, with the same rules as a pending alone; a number that is
    not in the batch changes nothing.

    True if it answered or discarded: it uses the quota of registration (§ 12).
    """
    match classification.pending_reply:
        case PendingReply.DISCARDS:
            close_batch(unit_of_work, batch, in_batch, PendingStatus.REJECTED, context.user.id)
            add_reply(unit_of_work, context, messages.BATCH_DISCARDED, ResponseKind.FIXED_TEXT)
            return True
        case PendingReply.CONTINUES:
            _answer_by_number(unit_of_work, context, batch, in_batch, classification)
            return True
        case PendingReply.OTHER_MOVEMENT | None:
            # Not about the batch: it keeps waiting, and the message gets its fixed text.
            # Another movement joins the batch before it gets here (CA-13).
            add_reply(unit_of_work, context, fixed_text(classification), ResponseKind.FIXED_TEXT)
            return False


def batch_question(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, in_batch: Sequence[PendingTransaction]
) -> str:
    """The list the open pendings of the batch got, as the model receives it with the reply."""
    items, _ = _open_items(unit_of_work, context, in_batch)
    return batch_list_text([_item_text(unit_of_work, context, item) for item in items])


def _answer_by_number(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    batch: PendingBatch,
    in_batch: Sequence[PendingTransaction],
    classification: Classification,
) -> None:
    """What the reply adds, changes or discards of each pending, and what follows: the batch
    registered, the list again, or the batch closed (CA-10, CA-11).
    """
    replies = {reply.number: reply for reply in classification.numbered_replies}
    items: list[_Item] = []
    notes: list[str] = []
    for pending in _open(in_batch):
        reply = replies.get(pending.position)
        if reply is not None and reply.discards:
            _reject(unit_of_work, context, pending)
            continue
        if reply is None:
            state = _stored_state(unit_of_work, context, pending)
            answered = pending
        else:
            state, answered = _continued_state(
                unit_of_work, context, pending, classification.for_pending(pending.position)
            )
        if isinstance(state, _CannotEnter):
            _reject(unit_of_work, context, answered)
            notes.append(not_registered_by_number(pending.position, state.reason))
            continue
        items.append(_Item(pending.position, state, answered, answered=reply is not None))
    _settle(unit_of_work, context, batch, items, notes, None)


def _continued_state(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    pending: PendingTransaction,
    reply: Classification,
) -> tuple[_State | _CannotEnter, PendingTransaction]:
    """What the reply makes of one pending, and the pending with its corrections counted."""
    if pending.intent is PendingIntent.TRANSFER:
        transfer, corrected = continued_transfer(context, pending, reply)
        return _transfer_state(context, transfer), corrected
    interpretation, corrected = continued_movement(unit_of_work, context, pending, reply)
    return _movement_state(unit_of_work, context, interpretation), corrected


def _open_items(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, in_batch: Sequence[PendingTransaction]
) -> tuple[list[_Item], list[str]]:
    """The open pendings of the batch, as they stand: what they kept, resolved again. One that
    can no longer be registered is named by its number instead.
    """
    items: list[_Item] = []
    notes: list[str] = []
    for pending in _open(in_batch):
        state = _stored_state(unit_of_work, context, pending)
        if isinstance(state, _CannotEnter):
            notes.append(not_registered_by_number(pending.position, state.reason))
        else:
            items.append(_Item(pending.position, state, pending))
    return items, notes


def _open(in_batch: Sequence[PendingTransaction]) -> list[PendingTransaction]:
    return [pending for pending in in_batch if pending.status is PendingStatus.OPEN]


def _new_state(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, single: Classification
) -> _State | _CannotEnter:
    """One movement of the message, resolved as if it came alone."""
    text, accounts, today = context.message.text, context.accounts, context.today
    if is_transfer(single):
        return _transfer_state(context, interpret_transfer(single, text, accounts, today))
    if is_movement(single):
        return _movement_state(unit_of_work, context, interpret(single, text, accounts, today))
    return _CannotEnter(fixed_text(single))


def _stored_state(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, pending: PendingTransaction
) -> _State | _CannotEnter:
    """An open pending, from what it kept, resolved the same way."""
    if pending.intent is PendingIntent.TRANSFER:
        transfer = transfer_from_parsed_data(pending.parsed_data, context.today)
        return _transfer_state(context, transfer)
    interpretation = from_parsed_data(pending.parsed_data, context.today)
    return _movement_state(unit_of_work, context, interpretation)


def _movement_state(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, interpretation: Interpretation
) -> _State | _CannotEnter:
    resolution = resolve_movement(unit_of_work, context, interpretation)
    match resolution:
        case ResolvedMovement():
            return _MovementToRegister(resolution, interpretation)
        case Missing():
            return resolution
        case BeforeAccountOpening():
            return _CannotEnter(
                before_opening_text(resolution.type, resolution.account.name, resolution.opened_on)
            )
        case NotYetSupported(several_periods=True):
            return _CannotEnter(messages.SEVERAL_PERIODS)
        case NotYetSupported():
            return _CannotEnter(messages.CANNOT_REGISTER_YET)


def _transfer_state(
    context: ReplyContext, interpretation: TransferInterpretation
) -> _State | _CannotEnter:
    resolution = resolve_user_transfer(context, interpretation)
    match resolution:
        case ResolvedTransfer():
            return _TransferToRegister(resolution, interpretation)
        case MissingTransfer():
            return resolution
        case TransferBeforeOpening():
            return _CannotEnter(
                transfer_before_opening_text(resolution.account.name, resolution.opened_on)
            )
        case DifferentCurrencies():
            return _CannotEnter(messages.TRANSFER_IN_DIFFERENT_CURRENCIES)
        case AnotherCurrencyThanItsAccounts():
            return _CannotEnter(messages.TRANSFER_IN_ANOTHER_CURRENCY)


def _settle(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    batch: PendingBatch | None,
    items: list[_Item],
    notes: list[str],
    overflow: str | None,
) -> None:
    """What the batch comes to: closed with nothing left, registered when every pending is
    complete, or the list that asks for what is missing. `batch` is None while it is new.
    """
    if not items:
        if batch is not None:
            close_batch(unit_of_work, batch, (), PendingStatus.REJECTED, context.user.id)
        text = _with_notes(None if notes else messages.BATCH_DISCARDED, notes, overflow)
        add_reply(unit_of_work, context, text, ResponseKind.FIXED_TEXT)
        return
    if all(isinstance(item.state, (_MovementToRegister, _TransferToRegister)) for item in items):
        _register(unit_of_work, context, batch, items, notes, overflow)
        return
    _ask(unit_of_work, context, batch, items, notes, overflow)


def _register(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    batch: PendingBatch | None,
    items: list[_Item],
    notes: list[str],
    overflow: str | None,
) -> None:
    """Every movement of the batch, and one confirmation: numbered with several, and the one of
    a movement alone with one (CA-5, CA-10). Each pending is promoted and the batch closes
    keeping the confirmation (domain rules, § 5).
    """
    user_id = context.user.id
    alone = len(items) == 1
    texts: list[str] = []
    # What each pending keeps, and the movement it became; a new batch comes after the reply.
    promoted: list[tuple[_Item, dict[str, str | None], Transaction | Transfer]] = []
    for item in items:
        position = None if alone else item.position
        if isinstance(item.state, _MovementToRegister):
            movement = item.state.movement
            transaction = new_transaction(context, movement)
            unit_of_work.transactions.add(transaction)
            texts.append(movement_confirmation(unit_of_work, movement, position))
            parsed = registered_parsed_data(movement, item.state.interpretation)
            promoted.append((item, parsed, transaction))
        elif isinstance(item.state, _TransferToRegister):
            resolved = item.state.transfer
            transfer = new_transfer(context, resolved)
            unit_of_work.transfers.add(transfer)
            texts.append(transfer_confirmation(resolved, position))
            parsed = transfer_to_parsed_data(registered(item.state.interpretation, resolved))
            promoted.append((item, parsed, transfer))
    main = texts[0] if alone else batch_confirmation_text(texts)
    confirmation = add_reply(
        unit_of_work, context, _with_notes(main, notes, overflow), ResponseKind.REGISTRATION
    )
    if batch is None:
        batch = closed_batch(context, confirmation)
        unit_of_work.pendings.add_batch(batch)
    else:
        unit_of_work.pendings.update_batch(
            replace(
                batch,
                awaiting_reply=False,
                confirmation_message_id=confirmation.id,
                status=BatchStatus.CLOSED,
            )
        )
    for item, parsed, result in promoted:
        pending = replace(
            item.pending
            or new_pending(context, batch, parsed, (), PendingStatus.PROMOTED, None, user_id),
            position=item.position,
            parsed_data=parsed,
            missing_fields=(),
            status=PendingStatus.PROMOTED,
            resolved_by=user_id,
        )
        if isinstance(result, Transaction):
            pending = replace(pending, resulting_transaction_id=result.id)
        else:
            pending = replace(
                pending, intent=PendingIntent.TRANSFER, resulting_transfer_id=result.id
            )
        if item.pending is None:
            unit_of_work.pendings.add(pending)
        else:
            unit_of_work.pendings.update(pending)


def _ask(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    batch: PendingBatch | None,
    items: list[_Item],
    notes: list[str],
    overflow: str | None,
) -> None:
    """The list of the batch, by number, and the pendings that keep what was understood: none
    is registered until all of them are complete (CA-8).
    """
    text = batch_list_text([_item_text(unit_of_work, context, item) for item in items])
    reply = add_reply(
        unit_of_work, context, _with_notes(text, notes, overflow), ResponseKind.REGISTRATION
    )
    if batch is None:
        batch = open_batch(context, reply)
        unit_of_work.pendings.add_batch(batch)
    else:
        unit_of_work.pendings.update_batch(replace(batch, question_message_id=reply.id))
    for item in items:
        parsed, fields, intent = _kept(item.state)
        if item.pending is None:
            new = new_pending(context, batch, parsed, fields, PendingStatus.OPEN, None, None)
            unit_of_work.pendings.add(replace(new, intent=intent, position=item.position))
        elif item.answered:
            unit_of_work.pendings.update(
                replace(item.pending, parsed_data=parsed, missing_fields=fields)
            )


def _item_text(unit_of_work: UnitOfWorkPort, context: ReplyContext, item: _Item) -> str:
    """One pending of the list: what was understood, and that it is complete or its question."""
    state = item.state
    match state:
        case _MovementToRegister(movement=movement):
            description = complete_movement_description(
                movement.type,
                movement.amount,
                movement.account.currency,
                movement.category.name,
                movement.account.name,
            )
            return batch_item_text(item.position, description, None)
        case _TransferToRegister(transfer=transfer):
            description = complete_transfer_description(
                transfer.amount,
                transfer.from_account.currency,
                transfer.from_account.name,
                transfer.to_account.name,
            )
            return batch_item_text(item.position, description, None)
        case Missing():
            return batch_item_text(
                item.position,
                movement_description(state, amount_currency(context, state)),
                movement_question(unit_of_work, context, state),
            )
        case MissingTransfer():
            return batch_item_text(
                item.position,
                transfer_description(state, transfer_currency(context, state)),
                transfer_question_text(state),
            )


def _kept(state: _State) -> tuple[dict[str, str | None], tuple[str, ...], PendingIntent]:
    """What an open pending keeps: what was understood, what it lacks, and what it becomes."""
    match state:
        case _MovementToRegister(movement=movement, interpretation=interpretation):
            return registered_parsed_data(movement, interpretation), (), PendingIntent.TRANSACTION
        case _TransferToRegister(transfer=transfer, interpretation=interpretation):
            parsed = transfer_to_parsed_data(registered(interpretation, transfer))
            return parsed, (), PendingIntent.TRANSFER
        case Missing():
            # Only the currency the messages said: the one of an account was never said.
            interpretation = state.interpretation
            fields = tuple(field.value for field in state.fields)
            parsed = to_parsed_data(interpretation, interpretation.currency)
            return parsed, fields, PendingIntent.TRANSACTION
        case MissingTransfer():
            fields = tuple(field.value for field in state.fields)
            return transfer_to_parsed_data(state.interpretation), fields, PendingIntent.TRANSFER


def _reject(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, pending: PendingTransaction
) -> None:
    unit_of_work.pendings.update(
        replace(pending, status=PendingStatus.REJECTED, resolved_by=context.user.id)
    )


def _with_notes(main: str | None, notes: list[str], overflow: str | None) -> str:
    """The reply, and after a blank line what did not enter the batch, each in a line of its own,
    and what did not fit.
    """
    parts = [] if main is None else [main]
    if notes:
        parts.append(LINE_END.join(notes))
    if overflow is not None:
        parts.append(overflow)
    return (LINE_END * 2).join(parts)
