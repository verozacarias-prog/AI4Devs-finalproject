"""What every flow of AnswerMessage shares: what it knows of the user, its reply, and
the pending and the batch it leaves (domain rules, § 5).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from app import messages
from app.constants import PENDING_VALIDITY_HOURS
from app.domain.entities.account import Account
from app.domain.entities.category import Category
from app.domain.entities.classification import (
    Classification,
    MessageClass,
)
from app.domain.entities.inbound_message import InboundMessage
from app.domain.entities.outbound_message import OutboundMessage, ResponseKind, reply_to
from app.domain.entities.pending_transaction import (
    BatchStatus,
    PendingBatch,
    PendingIntent,
    PendingSource,
    PendingStatus,
    PendingTransaction,
)
from app.domain.entities.user import User
from app.domain.ports.unit_of_work_port import UnitOfWorkPort

# The number of the only pending of a batch of one, and of the first of a batch of several.
FIRST_POSITION = 1


@dataclass(frozen=True)
class ReplyContext:
    """What the answer of one message needs to know of its user."""

    message: InboundMessage
    user: User
    accounts: list[Account]
    categories: list[Category]
    today: date
    now: datetime


def add_reply(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, text: str, kind: ResponseKind
) -> OutboundMessage:
    reply = reply_message(context.message, text, kind, context.now)
    unit_of_work.outbound_messages.add(reply)
    return reply


def reply_message(
    message: InboundMessage, text: str, kind: ResponseKind, now: datetime
) -> OutboundMessage:
    return reply_to(
        message.id, message.provider, message.user_id, message.from_phone, text, kind, now
    )


def new_pending(
    context: ReplyContext,
    batch: PendingBatch,
    parsed: dict[str, str | None],
    missing: tuple[str, ...],
    status: PendingStatus,
    transaction_id: uuid.UUID | None,
    resolved_by: uuid.UUID | None,
) -> PendingTransaction:
    return PendingTransaction(
        id=uuid.uuid4(),
        user_id=context.user.id,
        intent=PendingIntent.TRANSACTION,
        parsed_data=parsed,
        missing_fields=missing,
        source=PendingSource.MANUAL,
        batch_id=batch.id,
        position=FIRST_POSITION,
        resulting_transaction_id=transaction_id,
        status=status,
        resolved_by=resolved_by,
        expires_at=context.now + timedelta(hours=PENDING_VALIDITY_HOURS),
        created_at=context.now,
    )


def close_pending(
    unit_of_work: UnitOfWorkPort,
    awaiting: tuple[PendingBatch, PendingTransaction],
    status: PendingStatus,
    resolved_by: uuid.UUID | None,
) -> None:
    """The pending ends without a movement, rejected or expired, and its batch closes."""
    batch, pending = awaiting
    unit_of_work.pendings.update(replace(pending, status=status, resolved_by=resolved_by))
    unit_of_work.pendings.update_batch(
        replace(batch, awaiting_reply=False, status=BatchStatus.CLOSED)
    )


def reject(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
    text: str,
) -> None:
    if awaiting is not None:
        close_pending(unit_of_work, awaiting, PendingStatus.REJECTED, context.user.id)
    add_reply(unit_of_work, context, text, ResponseKind.FIXED_TEXT)


def ask_in_pending(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    question: str,
    parsed: dict[str, str | None],
    fields: tuple[str, ...],
    intent: PendingIntent,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> None:
    """The question, in the open pending or in a new one with its batch of one."""
    reply = add_reply(unit_of_work, context, question, ResponseKind.REGISTRATION)
    if awaiting is not None:
        batch, pending = awaiting
        unit_of_work.pendings.update(replace(pending, parsed_data=parsed, missing_fields=fields))
        unit_of_work.pendings.update_batch(replace(batch, question_message_id=reply.id))
        return
    batch = PendingBatch(
        id=uuid.uuid4(),
        user_id=context.user.id,
        source=PendingSource.MANUAL,
        awaiting_reply=True,
        question_message_id=reply.id,
        confirmation_message_id=None,
        status=BatchStatus.OPEN,
        created_at=context.now,
    )
    unit_of_work.pendings.add_batch(batch)
    unit_of_work.pendings.add(
        replace(
            new_pending(context, batch, parsed, fields, PendingStatus.OPEN, None, None),
            intent=intent,
        )
    )


def closed_batch(context: ReplyContext, confirmation: OutboundMessage) -> PendingBatch:
    """A batch registered from its first message: nothing was asked, and it keeps the
    confirmation.
    """
    return PendingBatch(
        id=uuid.uuid4(),
        user_id=context.user.id,
        source=PendingSource.MANUAL,
        awaiting_reply=False,
        question_message_id=None,
        confirmation_message_id=confirmation.id,
        status=BatchStatus.CLOSED,
        created_at=context.now,
    )


def fixed_text(classification: Classification) -> str:
    """What the assistant answers to what it cannot do yet (ADR 0018)."""
    if classification.message_class is MessageClass.REGISTRATION:
        return messages.CANNOT_REGISTER_YET
    if classification.message_class in (MessageClass.QUERY, MessageClass.ADVICE):
        return messages.CANNOT_ANSWER_YET
    return messages.ASK_FOR_DETAILS
