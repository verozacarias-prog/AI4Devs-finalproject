from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime

from app import messages
from app.domain.entities.account import Account
from app.domain.entities.category import Category
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    ModelUsage,
    NumberedPending,
    OpenBatch,
    PendingReply,
)
from app.domain.entities.inbound_message import InboundMessage, RetryPolicy
from app.domain.entities.llm_usage import UsageCounter, UsageLimits
from app.domain.entities.outbound_message import ResponseKind
from app.domain.entities.pending_transaction import (
    PendingBatch,
    PendingIntent,
    PendingStatus,
    PendingTransaction,
)
from app.domain.entities.transaction import TransactionType
from app.domain.entities.user import User
from app.domain.errors import ModelCallFailedError, ModelRefusedError, StoreUnavailableError
from app.domain.ports.llm_call_log_port import LlmCallLogPort
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.dates.local_date import local_today, start_of_day, start_of_next_day
from app.domain.services.transactions.movement_resolution import (
    Interpretation,
    from_parsed_data,
    interpret,
    is_movement,
    rejects_output,
)
from app.domain.services.transactions.pending_question import (
    transfer_question_text,
)
from app.domain.services.transactions.transfer_resolution import (
    interpret_transfer,
    is_transfer,
)
from app.domain.use_cases.messages.batch_registration import (
    answer_several,
    batch_question,
    continue_batch,
    join_batch,
)
from app.domain.use_cases.messages.movement_registration import (
    continue_movement,
    movement_missing_of,
    movement_question,
    settle_movement,
)
from app.domain.use_cases.messages.reply_context import (
    ReplyContext,
    add_reply,
    close_batch,
    fixed_text,
    reply_message,
)
from app.domain.use_cases.messages.transfer_registration import (
    continue_pending_transfer,
    settle_transfer,
    transfer_missing_of,
)
from app.shared.clock import Clock


@dataclass(frozen=True)
class LimitReached:
    """The user went over a daily counter, and the message was put off to their next day.

    `answered` says whether it got a notice: the one of the cap goes out once a day.
    """

    counter: UsageCounter
    answered: bool


@dataclass(frozen=True)
class ModelFailed:
    """The call to the model failed: the message was left for another attempt, or it failed."""

    error: ModelCallFailedError


# What the entry point learns of an answer besides how it ended, to log it (ADR 0023).
AnswerNotice = LimitReached | ModelFailed


def _ignore(notice: AnswerNotice) -> None:
    """Nobody listens: a test that only looks at what was stored."""


@dataclass(frozen=True)
class _Usage:
    """The user whose counters a message uses, and their day when it is processed (§ 12)."""

    user: User
    day: date
    now: datetime


@dataclass(frozen=True)
class _PaidCall:
    """The call that classified the message, which counts against the cap of the day with the
    tokens it took. One the model refused counts too; one that failed does not (ADR 0018,
    point 3).
    """

    usage: _Usage
    model: ModelUsage | None


@dataclass
class _Attempt:
    """What one attempt at a message already paid for, so that a failure after it still counts
    the call (issue #125): the transaction that counted it is undone with the failure.
    """

    paid: _PaidCall | None = None


@dataclass(frozen=True)
class _Loaded:
    """What answering a message needs of its user, read before calling the model."""

    usage: _Usage
    # How many messages the user already classified today: the total daily cap (§ 12).
    classified: int
    accounts: list[Account]
    categories: list[Category]
    # The day the user wrote, in their time zone.
    today: date
    # The batch that awaits a reply and its first open pending still valid, or else its first
    # open one; every pending of it, with those that expired already marked; and the open ones
    # that expired before the message was written, each at its own 24 hours (§ 5, CA-18).
    awaiting: tuple[PendingBatch, PendingTransaction] | None
    in_batch: tuple[PendingTransaction, ...]
    expired: tuple[PendingTransaction, ...]
    # The batch the message may answer: none if there is none, or if it expired (§ 5).
    open_batch: OpenBatch | None


class AnswerMessage:
    """Answers a message a worker took (ADR 0010, ADR 0018).

    One call to the model says what the message is, outside any transaction. Then the message
    is marked processed, and what it registers, what it leaves pending and its reply are
    stored, in one transaction, or none of it happens. If another worker took the message after
    this one, nothing is written: the attempts are the fencing token.

    A call that fails leaves the message for another attempt, until they are used up; a call
    the model refuses gets a fixed text at once, since trying again would get the same.

    With the daily cap of the user reached, the message is not classified; with the quota of
    registration used up, a registration is not interpreted. Either way it is put off to the
    next day of the user, and nothing is lost (domain rules, § 12).
    """

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        clock: Clock,
        llm: LLMPort,
        retries: RetryPolicy | None = None,
        limits: UsageLimits | None = None,
        calls: LlmCallLogPort | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._llm = llm
        self._retries = retries or RetryPolicy()
        self._limits = limits or UsageLimits()
        # Where a call whose output the validation rejects is marked: the same record the
        # wrapper of the model writes (ADR 0023, point 6).
        self._calls = calls

    def execute(
        self, message: InboundMessage, notify: Callable[[AnswerNotice], None] = _ignore
    ) -> bool:
        """True if this worker handled it; False if another one took it after this one.

        A failure that is not of the model is dealt with by its kind, and raised again so that
        the entry point logs it (CA-44): one that may go away is tried again later, and one
        whose state will not change leaves the message failed at once, with its notice. What
        the entry point logs besides, a limit reached or a call that failed, goes to `notify`.
        """
        attempt = _Attempt()
        try:
            return self._answer(message, notify, attempt)
        except StoreUnavailableError:
            self._try_again_later(message, attempt.paid)
            raise
        except Exception:
            self._fail(message, attempt.paid)
            raise

    def _answer(
        self,
        message: InboundMessage,
        notify: Callable[[AnswerNotice], None],
        attempt: _Attempt,
    ) -> bool:
        loaded = self._load(message)
        if loaded is None:
            # Only a registered user reaches the model; the web chat always has one.
            return self._store_reply(message, messages.ASK_FOR_DETAILS, ResponseKind.FIXED_TEXT)
        usage = loaded.usage
        if loaded.classified >= self._limits.classification:
            # Classifying costs too: it is not known whether it was an expense, so it waits.
            return self._put_off_by_the_cap(message, usage, notify)
        try:
            classification = self._llm.classify(
                _request(
                    message.text,
                    loaded.accounts,
                    loaded.categories,
                    loaded.today,
                    loaded.open_batch,
                )
            )
        except ModelRefusedError as error:
            return self._store_reply(
                message,
                messages.MODEL_REFUSED,
                ResponseKind.FIXED_TEXT,
                _PaidCall(usage, error.usage),
            )
        except ModelCallFailedError as error:
            notify(ModelFailed(error))
            # A fall of the provider does not use up the cap of the user (ADR 0018, point 3).
            return self._try_again_later(message)
        attempt.paid = _PaidCall(usage, classification.usage)
        return self._settle_message(message, loaded, classification, notify)

    def _load(self, message: InboundMessage) -> _Loaded | None:
        """What answering the message needs of its user, read before calling the model.

        None when the message is of no registered user.
        """
        with self._unit_of_work as unit_of_work:
            user_id = message.user_id
            user = None if user_id is None else unit_of_work.users.find_by_id(user_id)
            if user is None:
                return None
            now = self._clock.now()
            # The day of the counters is the one of the user when it is processed (§ 12).
            usage = _Usage(user, local_today(now, user.time_zone), now)
            accounts = unit_of_work.accounts.list_by_user(user.id)
            categories = unit_of_work.categories.list_available(user.id)
            # "Today" is the day the user wrote, in their time zone, not the day it is
            # processed.
            today = local_today(message.sent_at, user.time_zone)
            awaiting = unit_of_work.pendings.find_awaiting_reply(user.id)
            in_batch = (
                ()
                if awaiting is None
                else tuple(unit_of_work.pendings.list_in_batch(awaiting[0].id))
            )
            opened = [pending for pending in in_batch if pending.status is PendingStatus.OPEN]
            expired = tuple(pending for pending in opened if _expired(pending, message.sent_at))
            valid = [pending for pending in opened if pending not in expired]
            in_batch = tuple(
                replace(pending, status=PendingStatus.EXPIRED) if pending in expired else pending
                for pending in in_batch
            )
            open_batch = None
            if awaiting is not None and valid:
                awaiting = (awaiting[0], valid[0])
                context = ReplyContext(message, user, accounts, categories, today, message.sent_at)
                open_batch = _open_batch(unit_of_work, context, valid, alone=not expired)
            return _Loaded(
                usage=usage,
                classified=unit_of_work.llm_usage.count(
                    user.id, usage.day, UsageCounter.CLASSIFICATION
                ),
                accounts=accounts,
                categories=categories,
                today=today,
                awaiting=awaiting,
                in_batch=in_batch,
                expired=expired,
                open_batch=open_batch,
            )

    def _settle_message(
        self,
        message: InboundMessage,
        loaded: _Loaded,
        classification: Classification,
        notify: Callable[[AnswerNotice], None],
    ) -> bool:
        """What the classification says, in one transaction, or put off by the quota."""
        usage, awaiting = loaded.usage, loaded.awaiting
        continuing = awaiting is not None and loaded.open_batch is not None
        # Several open pendings are answered as a batch, and another movement joins it; so is a
        # pending left alone by others that expired, which the reply names (CA-18).
        alone = (
            loaded.open_batch is not None
            and len(loaded.open_batch.pendings) == 1
            and not loaded.expired
            and classification.pending_reply is not PendingReply.OTHER_MOVEMENT
        )
        if awaiting is not None and continuing and alone:
            # What the reply says of the pending it continues, by its number.
            classification = classification.for_pending(awaiting[1].position)
        # A pending transfer has no category whose name a reply could propose.
        previous = (
            from_parsed_data(awaiting[1].parsed_data, loaded.today)
            if awaiting is not None
            and continuing
            and alone
            and awaiting[1].intent is PendingIntent.TRANSACTION
            else None
        )
        self._mark_if_rejected(classification, message.text, previous)
        now = self._clock.now()
        context = ReplyContext(
            message, usage.user, loaded.accounts, loaded.categories, loaded.today, now
        )
        registration = _counts_as_registration(classification, continuing)
        with self._unit_of_work as unit_of_work:
            if (
                registration
                and unit_of_work.llm_usage.count(
                    usage.user.id, usage.day, UsageCounter.REGISTRATION
                )
                >= self._limits.registration
            ):
                return self._put_off_by_the_quota(
                    unit_of_work, message, usage, classification, notify
                )
            # First, so that a worker another one displaced writes nothing at all.
            if not unit_of_work.inbound_messages.mark_processed(message.id, message.attempts, now):
                return False
            _count(unit_of_work, usage, UsageCounter.CLASSIFICATION, classification.usage)
            if awaiting is not None and not continuing:
                # They all expired before this message was written: none is continued (§ 5).
                close_batch(unit_of_work, awaiting[0], loaded.expired, PendingStatus.EXPIRED, None)
            elif loaded.expired:
                # Some expired: they leave the batch, and the others go on (CA-18).
                for pending in loaded.expired:
                    unit_of_work.pendings.update(replace(pending, status=PendingStatus.EXPIRED))
            if awaiting is not None and continuing and alone:
                interpreted = _continue(unit_of_work, context, awaiting, classification)
            elif awaiting is not None and continuing:
                interpreted = _continue_batch(
                    unit_of_work, context, awaiting[0], loaded, classification
                )
            else:
                interpreted = _answer_new(unit_of_work, context, classification)
            # What got a fixed text because it cannot be registered yet uses no quota (C3-24).
            if interpreted:
                _count(unit_of_work, usage, UsageCounter.REGISTRATION, None)
            unit_of_work.commit()
        return True

    def _mark_if_rejected(
        self, classification: Classification, text: str, previous: Interpretation | None
    ) -> None:
        """Marks the call blocked when the checks in code drop something it returned (CA-47)."""
        if (
            self._calls is not None
            and classification.call_id is not None
            and rejects_output(classification, text, previous)
        ):
            self._calls.mark_blocked(classification.call_id)

    def _put_off_by_the_cap(
        self, message: InboundMessage, usage: _Usage, notify: Callable[[AnswerNotice], None]
    ) -> bool:
        """Put off to the next day without classifying, with the notice once a day (§ 12)."""
        time_zone = usage.user.time_zone
        with self._unit_of_work as unit_of_work:
            if not unit_of_work.inbound_messages.defer(
                message.id, message.attempts - 1, start_of_next_day(usage.now, time_zone)
            ):
                return False
            told = unit_of_work.outbound_messages.sent_since(
                usage.user.id, messages.DAILY_LIMIT_REACHED, start_of_day(usage.now, time_zone)
            )
            if not told:
                unit_of_work.outbound_messages.add(
                    reply_message(
                        message, messages.DAILY_LIMIT_REACHED, ResponseKind.FIXED_TEXT, usage.now
                    )
                )
            unit_of_work.commit()
        notify(LimitReached(UsageCounter.CLASSIFICATION, answered=not told))
        return True

    def _put_off_by_the_quota(
        self,
        unit_of_work: UnitOfWorkPort,
        message: InboundMessage,
        usage: _Usage,
        classification: Classification,
        notify: Callable[[AnswerNotice], None],
    ) -> bool:
        """A registration over the quota: put off to the next day, with its notice (§ 12).

        It was classified, and that counts against the cap; nothing it says is used.
        """
        next_day = start_of_next_day(usage.now, usage.user.time_zone)
        if not unit_of_work.inbound_messages.defer(message.id, message.attempts - 1, next_day):
            return False
        _count(unit_of_work, usage, UsageCounter.CLASSIFICATION, classification.usage)
        unit_of_work.outbound_messages.add(
            reply_message(
                message, messages.REGISTRATION_QUOTA_USED_UP, ResponseKind.FIXED_TEXT, usage.now
            )
        )
        unit_of_work.commit()
        notify(LimitReached(UsageCounter.REGISTRATION, answered=True))
        return True

    def _store_reply(
        self,
        message: InboundMessage,
        text: str,
        kind: ResponseKind,
        paid: _PaidCall | None = None,
    ) -> bool:
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            if not unit_of_work.inbound_messages.mark_processed(message.id, message.attempts, now):
                return False
            _count_paid(unit_of_work, paid)
            unit_of_work.outbound_messages.add(reply_message(message, text, kind, now))
            unit_of_work.commit()
        return True

    def _fail(self, message: InboundMessage, paid: _PaidCall | None = None) -> bool:
        """Failed for good, and its notice: the next message of the user is processed. A call
        to the model it already paid for counts against the cap of the day.
        """
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            if not unit_of_work.inbound_messages.mark_failed(message.id, message.attempts, now):
                return False
            _count_paid(unit_of_work, paid)
            unit_of_work.outbound_messages.add(
                reply_message(message, messages.MESSAGE_FAILED, ResponseKind.FIXED_TEXT, now)
            )
            unit_of_work.commit()
        return True

    def _try_again_later(self, message: InboundMessage, paid: _PaidCall | None = None) -> bool:
        """Another attempt with a growing wait, or, with them used up, failed and its notice. A
        call to the model this attempt already paid for counts either way: the retry pays its own.
        """
        if self._retries.is_last(message.attempts):
            return self._fail(message, paid)
        now = self._clock.now()
        next_attempt_at = now + self._retries.wait_after(message.attempts)
        with self._unit_of_work as unit_of_work:
            if not unit_of_work.inbound_messages.retry_later(
                message.id, message.attempts, next_attempt_at
            ):
                return False
            _count_paid(unit_of_work, paid)
            unit_of_work.commit()
        return True


def _counts_as_registration(classification: Classification, continuing: bool) -> bool:
    """Whether the message uses the quota of registration (domain rules, § 12).

    An expense, an income or a transfer to register or to add to the open batch, and the reply
    that answers or discards it.
    What gets a fixed text because it has no code yet uses none (docs/hoja-de-ruta.md).
    """
    if continuing and classification.pending_reply in (
        PendingReply.CONTINUES,
        PendingReply.DISCARDS,
    ):
        return True
    if continuing and classification.pending_reply is not PendingReply.OTHER_MOVEMENT:
        return False
    # A new message, or another movement that joins the batch (FEAT-007, CA-13).
    return classification.message_class is MessageClass.REGISTRATION and any(
        is_movement(single) or is_transfer(single)
        for single in map(classification.of_movement, classification.movements())
    )


def _count(
    unit_of_work: UnitOfWorkPort,
    usage: _Usage,
    counter: UsageCounter,
    model_usage: ModelUsage | None,
) -> None:
    """One more of that counter, with the tokens of the call when it is the one that paid it."""
    unit_of_work.llm_usage.add(
        usage.user.id,
        usage.day,
        counter,
        (model_usage.input_tokens or 0) if model_usage else 0,
        (model_usage.output_tokens or 0) if model_usage else 0,
    )


def _count_paid(unit_of_work: UnitOfWorkPort, paid: _PaidCall | None) -> None:
    """A message the model refused, or that failed or is retried after classifying, still counts
    against the cap of the day.
    """
    if paid is not None:
        _count(unit_of_work, paid.usage, UsageCounter.CLASSIFICATION, paid.model)


def _continue(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    awaiting: tuple[PendingBatch, PendingTransaction],
    classification: Classification,
) -> bool:
    """A message while a pending awaits its reply (domain rules, § 5). True if it completed or
    discarded it: it uses the quota of registration (§ 12).
    """
    if awaiting[1].intent is PendingIntent.TRANSFER:
        return continue_pending_transfer(unit_of_work, context, awaiting, classification)
    return continue_movement(unit_of_work, context, awaiting, classification)


def _continue_batch(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    batch: PendingBatch,
    loaded: _Loaded,
    classification: Classification,
) -> bool:
    """A message while a batch awaits its reply, as a batch: another movement joins it, and the
    reply to several pendings goes by number (FEAT-007). Those that expired are named.
    """
    in_batch, expired = loaded.in_batch, loaded.expired
    if classification.pending_reply is PendingReply.OTHER_MOVEMENT:
        return join_batch(unit_of_work, context, batch, in_batch, expired, classification)
    return continue_batch(unit_of_work, context, batch, in_batch, expired, classification)


def _answer_new(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, classification: Classification
) -> bool:
    """A message with no pending to continue. True if it was interpreted as a movement or a
    transfer: it uses the quota of registration (domain rules, § 12).
    """
    registration = classification.message_class is MessageClass.REGISTRATION
    if registration and classification.more_movements:
        return answer_several(unit_of_work, context, classification)
    if registration and is_transfer(classification):
        transfer = interpret_transfer(
            classification, context.message.text, context.accounts, context.today
        )
        return settle_transfer(unit_of_work, context, transfer, None)
    if registration and is_movement(classification):
        interpretation = interpret(
            classification, context.message.text, context.accounts, context.today
        )
        return settle_movement(unit_of_work, context, interpretation, None)
    add_reply(unit_of_work, context, fixed_text(classification), ResponseKind.FIXED_TEXT)
    return False


def _open_batch(
    unit_of_work: UnitOfWorkPort,
    context: ReplyContext,
    pendings: list[PendingTransaction],
    *,
    alone: bool,
) -> OpenBatch:
    """The batch as the model receives it: each open pending still valid with its number, and
    the question the user got. A single pending is a batch of one, with its own question, unless
    others of its batch expired (domain rules, § 5; CA-18).
    """
    question = (
        _pending_question(unit_of_work, context, pendings[0])
        if alone and len(pendings) == 1
        else batch_question(unit_of_work, context, pendings)
    )
    return OpenBatch(
        pendings=tuple(
            NumberedPending(
                number=pending.position,
                interpreted=dict(pending.parsed_data),
                missing=pending.missing_fields,
            )
            for pending in pendings
        ),
        question=question,
    )


def _pending_question(
    unit_of_work: UnitOfWorkPort, context: ReplyContext, pending: PendingTransaction
) -> str:
    """The question an open pending got, as the model receives it with the reply."""
    if pending.intent is PendingIntent.TRANSFER:
        return transfer_question_text(transfer_missing_of(context, pending))
    return movement_question(
        unit_of_work, context, movement_missing_of(unit_of_work, context, pending)
    )


def _expired(pending: PendingTransaction, written_at: datetime) -> bool:
    """Whether it expired before the message was written: a late answer does not count."""
    return pending.expires_at is not None and pending.expires_at <= written_at


def _request(
    text: str,
    accounts: list[Account],
    categories: list[Category],
    today: date,
    open_batch: OpenBatch | None,
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
        open_batch=open_batch,
    )
