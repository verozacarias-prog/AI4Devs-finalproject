from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal

from app import messages
from app.constants import LINE_END, PENDING_VALIDITY_HOURS
from app.domain.entities.account import Account
from app.domain.entities.budget_period import PeriodStatus
from app.domain.entities.category import Category
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    OpenPending,
    PendingReply,
)
from app.domain.entities.inbound_message import InboundMessage, RetryPolicy
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
from app.domain.entities.user import User
from app.domain.errors import ModelCallFailedError, ModelRefusedError, StoreUnavailableError
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.dates.local_date import local_today
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
    interpret,
    is_movement,
    proposes_an_unwritten_name,
    resolve,
    same_name,
    to_parsed_data,
)
from app.domain.services.transactions.pending_question import question_text
from app.domain.services.transactions.registration_confirmation import (
    before_opening_text,
    confirmation_text,
)
from app.shared.clock import Clock

# The only pending of a batch in delivery 2: more than one comes with the final delivery.
_FIRST_POSITION = 1


@dataclass(frozen=True)
class _Context:
    """What the answer of one message needs to know of its user."""

    message: InboundMessage
    user: User
    accounts: list[Account]
    categories: list[Category]
    today: date
    now: datetime


class AnswerMessage:
    """Answers a message a worker took (ADR 0010, ADR 0018).

    One call to the model says what the message is, outside any transaction. Then the message
    is marked processed, and what it registers, what it leaves pending and its reply are
    stored, in one transaction, or none of it happens. If another worker took the message after
    this one, nothing is written: the attempts are the fencing token.

    A call that fails leaves the message for another attempt, until they are used up; a call
    the model refuses gets a fixed text at once, since trying again would get the same.
    """

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        clock: Clock,
        llm: LLMPort,
        retries: RetryPolicy | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._llm = llm
        self._retries = retries or RetryPolicy()

    def execute(self, message: InboundMessage) -> bool:
        """True if this worker handled it; False if another one took it after this one.

        A failure that is not of the model is dealt with by its kind, and raised again so that
        the entry point logs it (CA-44): one that may go away is tried again later, and one
        whose state will not change leaves the message failed at once, with its notice.
        """
        try:
            return self._answer(message)
        except StoreUnavailableError:
            self._try_again_later(message)
            raise
        except Exception:
            self._fail(message)
            raise

    def _answer(self, message: InboundMessage) -> bool:
        user_id = message.user_id
        awaiting: tuple[PendingBatch, PendingTransaction] | None = None
        question: str | None = None
        with self._unit_of_work as unit_of_work:
            user = None if user_id is None else unit_of_work.users.find_by_id(user_id)
            if user is not None:
                accounts = unit_of_work.accounts.list_by_user(user.id)
                categories = unit_of_work.categories.list_available(user.id)
                # "Today" is the day the user wrote, in their time zone, not the day it is
                # processed.
                today = local_today(message.sent_at, user.time_zone)
                awaiting = unit_of_work.pendings.find_awaiting_reply(user.id)
                if awaiting is not None and not _expired(awaiting[1], message.sent_at):
                    context = _Context(message, user, accounts, categories, today, message.sent_at)
                    question = _question_of(unit_of_work, context, awaiting[1])
        if user_id is None or user is None:
            # Only a registered user reaches the model; the web chat always has one.
            return self._store_reply(message, messages.ASK_FOR_DETAILS, ResponseKind.FIXED_TEXT)
        open_pending = None
        if awaiting is not None and question is not None:
            open_pending = OpenPending(
                interpreted=dict(awaiting[1].parsed_data),
                missing=awaiting[1].missing_fields,
                question=question,
            )
        try:
            classification = self._llm.classify(
                _request(message.text, accounts, categories, today, open_pending)
            )
        except ModelRefusedError:
            return self._store_reply(message, messages.MODEL_REFUSED, ResponseKind.FIXED_TEXT)
        except ModelCallFailedError:
            return self._try_again_later(message)
        now = self._clock.now()
        context = _Context(message, user, accounts, categories, today, now)
        with self._unit_of_work as unit_of_work:
            # First, so that a worker another one displaced writes nothing at all.
            if not unit_of_work.inbound_messages.mark_processed(message.id, message.attempts, now):
                return False
            if awaiting is not None and open_pending is None:
                # It expired before this message was written: it is not continued (§ 5).
                _close(unit_of_work, awaiting, PendingStatus.EXPIRED, None)
            if awaiting is not None and open_pending is not None:
                _continue(unit_of_work, context, awaiting, classification)
            else:
                _answer_new(unit_of_work, context, classification)
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

    def _fail(self, message: InboundMessage) -> bool:
        """Failed for good, and its notice: the next message of the user is processed."""
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            if not unit_of_work.inbound_messages.mark_failed(message.id, message.attempts, now):
                return False
            unit_of_work.outbound_messages.add(
                _reply(message, messages.MESSAGE_FAILED, ResponseKind.FIXED_TEXT, now)
            )
            unit_of_work.commit()
        return True

    def _try_again_later(self, message: InboundMessage) -> bool:
        """Another attempt with a growing wait, or, with them used up, failed and its notice."""
        if self._retries.is_last(message.attempts):
            return self._fail(message)
        now = self._clock.now()
        next_attempt_at = now + self._retries.wait_after(message.attempts)
        with self._unit_of_work as unit_of_work:
            if not unit_of_work.inbound_messages.retry_later(
                message.id, message.attempts, next_attempt_at
            ):
                return False
            unit_of_work.commit()
        return True


def _answer_new(
    unit_of_work: UnitOfWorkPort, context: _Context, classification: Classification
) -> None:
    """A message with no pending to continue."""
    if classification.message_class is MessageClass.REGISTRATION and is_movement(classification):
        if classification.several_movements:
            # Several movements in a message belong to the final delivery (CA-16).
            _add_reply(unit_of_work, context, messages.CANNOT_REGISTER_YET, ResponseKind.FIXED_TEXT)
            return
        interpretation = interpret(
            classification, context.message.text, context.accounts, context.today
        )
        _settle(unit_of_work, context, interpretation, None)
        return
    _add_reply(unit_of_work, context, _fixed_text(classification), ResponseKind.FIXED_TEXT)


def _continue(
    unit_of_work: UnitOfWorkPort,
    context: _Context,
    awaiting: tuple[PendingBatch, PendingTransaction],
    classification: Classification,
) -> None:
    """A message while a pending awaits its reply (domain rules, § 5)."""
    batch, pending = awaiting
    match classification.pending_reply:
        case PendingReply.DISCARDS:
            _close(unit_of_work, awaiting, PendingStatus.REJECTED, context.user.id)
            _add_reply(unit_of_work, context, messages.PENDING_DISCARDED, ResponseKind.FIXED_TEXT)
        case PendingReply.OTHER_MOVEMENT:
            # One at a time in delivery 2: the new one is not registered (CA-36).
            question = _question_of(unit_of_work, context, pending)
            reply = _add_reply(
                unit_of_work,
                context,
                LINE_END.join((messages.FINISH_THE_PENDING_FIRST, question)),
                ResponseKind.REGISTRATION,
            )
            unit_of_work.pendings.update_batch(replace(batch, question_message_id=reply.id))
        case PendingReply.CONTINUES:
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
                interpretation = _accept_proposal(
                    unit_of_work, context, pending, previous, interpretation
                )
            _settle(unit_of_work, context, interpretation, (batch, corrected))
        case None:
            # Not about the pending: it keeps waiting, and the message gets its fixed text.
            _add_reply(unit_of_work, context, _fixed_text(classification), ResponseKind.FIXED_TEXT)


def _accept_proposal(
    unit_of_work: UnitOfWorkPort,
    context: _Context,
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
    unit_of_work: UnitOfWorkPort, context: _Context, name: str, kind: TransactionType
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


def _settle(
    unit_of_work: UnitOfWorkPort,
    context: _Context,
    interpretation: Interpretation,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> None:
    """Registers it, says why not, or asks what is missing, in a new pending or in the open one."""
    resolution = _resolve(unit_of_work, context, interpretation)
    match resolution:
        case ResolvedMovement():
            _register(unit_of_work, context, resolution, interpretation, awaiting)
        case BeforeAccountOpening():
            text = before_opening_text(
                resolution.type, resolution.account.name, resolution.opened_on
            )
            _reject(unit_of_work, context, awaiting, text)
        case NotYetSupported():
            _reject(unit_of_work, context, awaiting, messages.CANNOT_REGISTER_YET)
        case Missing():
            _ask(unit_of_work, context, resolution, awaiting)


def _resolve(
    unit_of_work: UnitOfWorkPort, context: _Context, interpretation: Interpretation
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


def _reject(
    unit_of_work: UnitOfWorkPort,
    context: _Context,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
    text: str,
) -> None:
    if awaiting is not None:
        _close(unit_of_work, awaiting, PendingStatus.REJECTED, context.user.id)
    _add_reply(unit_of_work, context, text, ResponseKind.FIXED_TEXT)


def _ask(
    unit_of_work: UnitOfWorkPort,
    context: _Context,
    missing: Missing,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> None:
    """The question, and the pending that keeps what was understood (§ 5)."""
    reply = _add_reply(
        unit_of_work, context, _question(unit_of_work, context, missing), ResponseKind.REGISTRATION
    )
    currency = None if missing.account is None else missing.account.currency
    parsed = to_parsed_data(missing.interpretation, currency)
    fields = tuple(field.value for field in missing.fields)
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
        _pending(context, batch, parsed, fields, PendingStatus.OPEN, None, None)
    )


def _question(unit_of_work: UnitOfWorkPort, context: _Context, missing: Missing) -> str:
    currency = (
        context.user.primary_currency if missing.account is None else missing.account.currency
    )
    limits: list[tuple[str, Decimal]] = []
    if missing.draft is not None:
        names = {category.id: category.name for category in context.categories}
        limits = sorted(
            (names[budget.category_id], budget.limit_amount)
            for budget in unit_of_work.budgets.list_by_period(missing.draft.id)
            if budget.category_id in names
        )
    return question_text(missing, currency, limits)


def _question_of(
    unit_of_work: UnitOfWorkPort, context: _Context, pending: PendingTransaction
) -> str:
    """The question of an open pending, as it was asked: from what it kept, the same way."""
    interpretation = from_parsed_data(pending.parsed_data, context.today)
    resolution = _resolve(unit_of_work, context, interpretation)
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
    return _question(unit_of_work, context, resolution)


def _register(
    unit_of_work: UnitOfWorkPort,
    context: _Context,
    movement: ResolvedMovement,
    interpretation: Interpretation,
    awaiting: tuple[PendingBatch, PendingTransaction] | None,
) -> None:
    """The movement and its confirmation. Its pending is promoted and its batch closed, the open
    one or a new batch of one (domain rules, § 5): the batch keeps the confirmation, so quoting
    it later finds the movement.
    """
    user_id = context.user.id
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
    group_id = movement.period.family_group_id
    group = None if group_id is None else unit_of_work.family_groups.find_by_id(group_id)
    confirmation = _add_reply(
        unit_of_work,
        context,
        confirmation_text(
            type=movement.type,
            amount=movement.amount,
            currency=currency,
            account_name=movement.account.name,
            category_name=movement.category.name,
            transaction_date=movement.transaction_date,
            period=movement.period,
            group_name=None if group is None else group.name,
        ),
        ResponseKind.REGISTRATION,
    )
    parsed = to_parsed_data(
        replace(interpretation, account=movement.account.name, category=movement.category.name),
        currency,
    )
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
    batch = PendingBatch(
        id=uuid.uuid4(),
        user_id=user_id,
        source=PendingSource.MANUAL,
        awaiting_reply=False,
        question_message_id=None,
        confirmation_message_id=confirmation.id,
        status=BatchStatus.CLOSED,
        created_at=context.now,
    )
    unit_of_work.pendings.add_batch(batch)
    unit_of_work.pendings.add(
        _pending(context, batch, parsed, (), PendingStatus.PROMOTED, transaction.id, user_id)
    )


def _pending(
    context: _Context,
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
        position=_FIRST_POSITION,
        resulting_transaction_id=transaction_id,
        status=status,
        resolved_by=resolved_by,
        expires_at=context.now + timedelta(hours=PENDING_VALIDITY_HOURS),
        created_at=context.now,
    )


def _close(
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


def _expired(pending: PendingTransaction, written_at: datetime) -> bool:
    """Whether it expired before the message was written: a late answer does not count."""
    return pending.expires_at is not None and pending.expires_at <= written_at


def _request(
    text: str,
    accounts: list[Account],
    categories: list[Category],
    today: date,
    open_pending: OpenPending | None,
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
        open_pending=open_pending,
    )


def _fixed_text(classification: Classification) -> str:
    """What the assistant answers to what it cannot do yet (ADR 0018)."""
    if classification.message_class is MessageClass.REGISTRATION:
        return messages.CANNOT_REGISTER_YET
    if classification.message_class in (MessageClass.QUERY, MessageClass.ADVICE):
        return messages.CANNOT_ANSWER_YET
    return messages.ASK_FOR_DETAILS


def _add_reply(
    unit_of_work: UnitOfWorkPort, context: _Context, text: str, kind: ResponseKind
) -> OutboundMessage:
    reply = _reply(context.message, text, kind, context.now)
    unit_of_work.outbound_messages.add(reply)
    return reply


def _reply(
    message: InboundMessage, text: str, kind: ResponseKind, now: datetime
) -> OutboundMessage:
    return reply_to(
        message.id, message.provider, message.user_id, message.from_phone, text, kind, now
    )
