"""Several movements in one message, in AnswerMessage: registered together in one batch
(FEAT-007).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app import messages
from app.domain.entities.classification import (
    Classification,
)
from app.domain.entities.outbound_message import ResponseKind
from app.domain.entities.pending_transaction import (
    PendingIntent,
    PendingStatus,
)
from app.domain.entities.transaction import Transaction
from app.domain.entities.transfer import Transfer
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.transactions.movement_resolution import (
    Interpretation,
    ResolvedMovement,
    interpret,
    is_movement,
)
from app.domain.services.transactions.registration_confirmation import (
    batch_confirmation_text,
)
from app.domain.services.transactions.transfer_resolution import (
    ResolvedTransfer,
    TransferInterpretation,
    interpret_transfer,
    is_transfer,
    registered,
    transfer_to_parsed_data,
)
from app.domain.use_cases.messages.movement_registration import (
    movement_confirmation,
    new_transaction,
    registered_parsed_data,
    resolve_movement,
)

# The number of the only pending of a batch of one, and of the first of a batch of several.
from app.domain.use_cases.messages.reply_context import (
    FIRST_POSITION,
    ReplyContext,
    add_reply,
    closed_batch,
    new_pending,
)
from app.domain.use_cases.messages.transfer_registration import (
    new_transfer,
    resolve_user_transfer,
    transfer_confirmation,
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


def answer_several(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, classification: Classification
) -> bool:
    """A message with several movements (FEAT-007). Each one is resolved as if it came alone,
    and when all of them are complete they are registered together, in one batch. Otherwise,
    until the second cut, the message gets the fixed text and nothing is registered.
    """
    resolved: list[_MovementToRegister | _TransferToRegister] = []
    for single in map(classification.of_movement, classification.movements()):
        if is_transfer(single):
            transfer = interpret_transfer(
                single, context.message.text, context.accounts, context.today
            )
            transfer_resolution = resolve_user_transfer(context, transfer)
            if isinstance(transfer_resolution, ResolvedTransfer):
                resolved.append(_TransferToRegister(transfer_resolution, transfer))
                continue
        elif is_movement(single):
            interpretation = interpret(
                single, context.message.text, context.accounts, context.today
            )
            resolution = resolve_movement(unit_of_work, context, interpretation)
            if isinstance(resolution, ResolvedMovement):
                resolved.append(_MovementToRegister(resolution, interpretation))
                continue
        add_reply(unit_of_work, context, messages.CANNOT_REGISTER_YET, ResponseKind.FIXED_TEXT)
        return False
    _register_batch(unit_of_work, context, resolved)
    return True


def _register_batch(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    resolved: list[_MovementToRegister | _TransferToRegister],
) -> None:
    """Every movement of the batch, and one confirmation that lists them by number. Each pending
    is promoted, in the order of the message, and the batch closes keeping the confirmation
    (domain rules, § 5).
    """
    user_id = context.user.id
    texts: list[str] = []
    # What each pending keeps, and the movement it became; the batch comes after the reply.
    promoted: list[tuple[dict[str, str | None], Transaction | Transfer]] = []
    for position, item in enumerate(resolved, start=FIRST_POSITION):
        if isinstance(item, _MovementToRegister):
            transaction = new_transaction(context, item.movement)
            unit_of_work.transactions.add(transaction)
            texts.append(movement_confirmation(unit_of_work, item.movement, position))
            promoted.append(
                (registered_parsed_data(item.movement, item.interpretation), transaction)
            )
        else:
            transfer = new_transfer(context, item.transfer)
            unit_of_work.transfers.add(transfer)
            texts.append(transfer_confirmation(item.transfer, position))
            parsed = transfer_to_parsed_data(registered(item.interpretation, item.transfer))
            promoted.append((parsed, transfer))
    confirmation = add_reply(
        unit_of_work, context, batch_confirmation_text(texts), ResponseKind.REGISTRATION
    )
    batch = closed_batch(context, confirmation)
    unit_of_work.pendings.add_batch(batch)
    for position, (parsed, result) in enumerate(promoted, start=FIRST_POSITION):
        pending = new_pending(context, batch, parsed, (), PendingStatus.PROMOTED, None, user_id)
        if isinstance(result, Transaction):
            pending = replace(pending, resulting_transaction_id=result.id)
        else:
            pending = replace(
                pending, intent=PendingIntent.TRANSFER, resulting_transfer_id=result.id
            )
        unit_of_work.pendings.add(replace(pending, position=position))
