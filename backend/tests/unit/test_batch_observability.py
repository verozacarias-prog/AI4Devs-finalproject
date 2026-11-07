"""What a batch of several movements leaves to measure, with the ports replaced (FEAT-007).

Cases C3-02, C3-03 and C3-05 to C3-07 of its spec.md: the fields that came empty in any movement,
the corrections of each pending, and the call marked `blocked` when the code drops what the
model returned of any movement or of any pending. The database is in memory and nothing reaches
the provider.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from app.adapters.observability.llm_calls import RecordedLLM
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    MovementReading,
    NumberedReply,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.llm_call import OutputField
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryLlmCallLog, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, OCTOBER_17, Lucia


def _expense(amount: str, account: str | None, category: str) -> MovementReading:
    return MovementReading(
        registration_type=RegistrationType.EXPENSE,
        amount=Decimal(amount),
        account=account,
        category=category,
    )


def _registration(first: MovementReading, *more: MovementReading) -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=first.registration_type,
        amount=first.amount,
        account=first.account,
        category=first.category,
        more_movements=more,
    )


def _by_number(*replies: NumberedReply) -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        pending_reply=PendingReply.CONTINUES,
        numbered_replies=replies,
    )


def _answer(
    unit_of_work: InMemoryUnitOfWork,
    lucia: Lucia,
    calls: InMemoryLlmCallLog,
    text: str,
    classification: Classification,
    *,
    minutes_later: int = 0,
) -> None:
    """Answers the message with the model behind the wrapper that records its calls."""
    now = NOW + timedelta(minutes=minutes_later)
    llm = RecordedLLM(FakeLLM(classification), calls)
    AnswerMessage(unit_of_work, FixedClock(now), llm, calls=calls).execute(
        lucia.message(text, sent_at=now - timedelta(seconds=5))
    )


def _supermarket_and_nafta(
    unit_of_work: InMemoryUnitOfWork, lucia: Lucia, calls: InMemoryLlmCallLog
) -> None:
    """The batch of C2-01: the supermarket with MP, complete, and the nafta with no account."""
    _answer(
        unit_of_work,
        lucia,
        calls,
        "gasté 3500 en el súper con MP y 1200 de nafta",
        _registration(_expense("3500", "MP", "Supermercado"), _expense("1200", None, "Transporte")),
    )


def test_the_row_of_the_classification_lists_the_empty_fields_of_any_movement() -> None:
    # Case C3-02.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    calls = InMemoryLlmCallLog()

    _supermarket_and_nafta(unit_of_work, lucia, calls)

    [call] = calls.recorded
    assert call.empty_fields == (
        OutputField.ACCOUNT,
        OutputField.CURRENCY,
        OutputField.TRANSACTION_DATE,
    )


def test_a_reply_by_number_adds_the_correction_only_to_the_pending_it_changes() -> None:
    # Case C3-03.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    calls = InMemoryLlmCallLog()
    _supermarket_and_nafta(unit_of_work, lucia, calls)

    _answer(
        unit_of_work,
        lucia,
        calls,
        "el 2 fueron 1300 en efectivo",
        _by_number(
            NumberedReply(
                number=2, reading=MovementReading(amount=Decimal("1300"), account="efectivo")
            )
        ),
        minutes_later=1,
    )

    assert sorted(transaction.amount for transaction in unit_of_work.transactions.added) == [
        Decimal("1300.00"),
        Decimal("3500.00"),
    ]
    corrected = {
        pending.position: pending.corrected_fields_count for pending in unit_of_work.pendings.added
    }
    assert corrected == {1: 0, 2: 1}


def test_an_account_not_written_in_the_second_movement_leaves_the_call_blocked() -> None:
    # Case C3-05.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    calls = InMemoryLlmCallLog()

    _answer(
        unit_of_work,
        lucia,
        calls,
        "gasté 3500 en el súper con MP y 1200 de nafta",
        _registration(
            _expense("3500", "MP", "Supermercado"), _expense("1200", "Brubank", "Transporte")
        ),
    )

    [call] = calls.recorded
    assert calls.blocked == [call.id]
    second = next(pending for pending in unit_of_work.pendings.added if pending.position == 2)
    assert second.missing_fields == ("account_id",)


def test_an_account_not_written_in_a_reply_by_number_leaves_the_call_blocked() -> None:
    # Case C3-06.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    calls = InMemoryLlmCallLog()
    _supermarket_and_nafta(unit_of_work, lucia, calls)

    _answer(
        unit_of_work,
        lucia,
        calls,
        "el 2 en efectivo",
        _by_number(NumberedReply(number=2, reading=MovementReading(account="Mercado Pago"))),
        minutes_later=1,
    )

    reply_call = calls.recorded[-1]
    assert calls.blocked == [reply_call.id]
    second = next(pending for pending in unit_of_work.pendings.added if pending.position == 2)
    assert second.missing_fields == ("account_id",)


def test_with_no_open_batch_the_row_lists_the_empty_fields_of_the_movements() -> None:
    # Case C3-07.
    calls = InMemoryLlmCallLog()
    llm = RecordedLLM(
        FakeLLM(
            Classification(
                MessageClass.REGISTRATION,
                pending_reply=PendingReply.CONTINUES,
                numbered_replies=(
                    NumberedReply(number=1, reading=MovementReading(amount=Decimal("100"))),
                ),
                registration_type=RegistrationType.EXPENSE,
                amount=Decimal("3500"),
                account="MP",
                category="Supermercado",
            )
        ),
        calls,
    )

    llm.classify(
        ClassificationRequest(
            "gasté 3500 en el súper con MP",
            ("Mercado Pago",),
            ("Supermercado",),
            ("Sueldo",),
            OCTOBER_17,
        )
    )

    [call] = calls.recorded
    assert call.empty_fields == (OutputField.CURRENCY, OutputField.TRANSACTION_DATE)
