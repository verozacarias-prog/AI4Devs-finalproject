from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from app import messages
from app.constants import PENDING_VALIDITY_HOURS
from app.domain.entities.account import Account
from app.domain.entities.category import Category
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
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
from app.domain.entities.transaction import Transaction, TransactionSource, TransactionType
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.dates.local_date import local_today
from app.domain.services.transactions.movement_resolution import (
    ResolvedMovement,
    is_movement,
    movement_date,
    resolve_movement,
)
from app.domain.services.transactions.registration_confirmation import confirmation_text
from app.shared.clock import Clock


class AnswerMessage:
    """Answers a message a worker took (ADR 0010, ADR 0018).

    One call to the model says what the message is, outside any transaction. Then the message
    is marked processed, and what it registers and its reply are stored, in one transaction,
    or none of it happens. If another worker took the message after this one, nothing is
    written: the attempts are the fencing token.
    """

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock, llm: LLMPort) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._llm = llm

    def execute(self, message: InboundMessage) -> bool:
        """True if this worker answered it; False if another one took it after this one."""
        user_id = message.user_id
        with self._unit_of_work as unit_of_work:
            user = None if user_id is None else unit_of_work.users.find_by_id(user_id)
            if user is not None:
                accounts = unit_of_work.accounts.list_by_user(user.id)
                categories = unit_of_work.categories.list_available(user.id)
        if user_id is None or user is None:
            # Only a registered user reaches the model; the web chat always has one.
            return self._store_reply(message, messages.ASK_FOR_DETAILS, ResponseKind.FIXED_TEXT)
        # "Today" is the day the user wrote, in their time zone, not the day it is processed.
        today = local_today(message.sent_at, user.time_zone)
        classification = self._llm.classify(_request(message.text, accounts, categories, today))
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            # First, so that a worker another one displaced writes nothing at all.
            if not unit_of_work.inbound_messages.mark_processed(message.id, message.attempts, now):
                return False
            movement = None
            if is_movement(classification):
                periods = unit_of_work.budget_periods.list_covering(
                    user_id, movement_date(classification, today)
                )
                movement = resolve_movement(
                    classification, accounts, categories, today, user.time_zone, periods
                )
            if movement is not None:
                _register(unit_of_work, message, user_id, movement, now)
            else:
                text = _fixed_text(classification)
                unit_of_work.outbound_messages.add(
                    _reply(message, text, ResponseKind.FIXED_TEXT, now)
                )
            unit_of_work.commit()
        return True

    def _store_reply(self, message: InboundMessage, text: str, kind: ResponseKind) -> bool:
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            if not unit_of_work.inbound_messages.mark_processed(message.id, message.attempts, now):
                return False
            unit_of_work.outbound_messages.add(_reply(message, text, kind, now))
            unit_of_work.commit()
        return True


def _request(
    text: str, accounts: list[Account], categories: list[Category], today: date
) -> ClassificationRequest:
    return ClassificationRequest(
        text=text,
        accounts=tuple(account.name for account in accounts),
        expense_categories=tuple(
            category.name for category in categories if category.kind is TransactionType.EXPENSE
        ),
        income_categories=tuple(
            category.name for category in categories if category.kind is TransactionType.INCOME
        ),
        today=today,
    )


def _fixed_text(classification: Classification) -> str:
    """What the assistant answers to what it cannot do yet (ADR 0018)."""
    if classification.message_class is MessageClass.REGISTRATION:
        return messages.CANNOT_REGISTER_YET
    if classification.message_class in (MessageClass.QUERY, MessageClass.ADVICE):
        return messages.CANNOT_ANSWER_YET
    return messages.ASK_FOR_DETAILS


def _reply(
    message: InboundMessage, text: str, kind: ResponseKind, now: datetime
) -> OutboundMessage:
    return reply_to(
        message.id, message.provider, message.user_id, message.from_phone, text, kind, now
    )


def _register(
    unit_of_work: UnitOfWorkPort,
    message: InboundMessage,
    user_id: uuid.UUID,
    movement: ResolvedMovement,
    now: datetime,
) -> None:
    """The movement, its confirmation, and its batch of one, closed at once (domain rules, § 5).

    The batch keeps the confirmation, so quoting it later finds the movement.
    """
    currency = movement.account.currency
    transaction = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=movement.account.id,
        type=movement.type,
        amount=movement.amount,
        currency=currency,
        exchange_rate=None,
        transaction_date=movement.transaction_date,
        budget_period_id=movement.period.id,
        category_id=movement.category.id,
        source=TransactionSource.MANUAL,
    )
    unit_of_work.transactions.add(transaction)
    confirmation = _reply(
        message,
        confirmation_text(
            type=movement.type,
            amount=movement.amount,
            currency=currency,
            account_name=movement.account.name,
            category_name=movement.category.name,
            transaction_date=movement.transaction_date,
            period=movement.period,
        ),
        ResponseKind.REGISTRATION,
        now,
    )
    unit_of_work.outbound_messages.add(confirmation)
    batch = PendingBatch(
        id=uuid.uuid4(),
        user_id=user_id,
        source=PendingSource.MANUAL,
        awaiting_reply=False,
        question_message_id=None,
        confirmation_message_id=confirmation.id,
        status=BatchStatus.CLOSED,
        created_at=now,
    )
    unit_of_work.pendings.add_batch(batch)
    unit_of_work.pendings.add(
        PendingTransaction(
            id=uuid.uuid4(),
            user_id=user_id,
            intent=PendingIntent.TRANSACTION,
            parsed_data={
                "type": movement.type,
                "amount": str(movement.amount),
                "currency": currency,
                "account": movement.account.name,
                "category": movement.category.name,
                "transaction_date": movement.transaction_date.isoformat(),
            },
            missing_fields=(),
            source=PendingSource.MANUAL,
            batch_id=batch.id,
            position=1,
            resulting_transaction_id=transaction.id,
            status=PendingStatus.PROMOTED,
            resolved_by=user_id,
            expires_at=now + timedelta(hours=PENDING_VALIDITY_HOURS),
            created_at=now,
        )
    )
