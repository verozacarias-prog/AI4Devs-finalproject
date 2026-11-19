"""The regression set of the classification prompt, with the model replaced (issue 157).

Cases A1 to A10 of the task, approved on 17/11/2026, and A11, approved on 19/11/2026: how the
set announces a run, scores what the model returned, counts what the code would drop, the calls
that gave no answer and what they cost, and compares two runs. Nothing here reaches the
provider.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    ModelUsage,
    MovementReading,
    NumberedPending,
    NumberedReply,
    OpenBatch,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelAnswerCutError, ModelCallFailedError, ModelRefusedError
from app.domain.ports.llm_port import LLMPort
from evals.classification.regression import compare, run_regression
from evals.classification.regression_case import RegressionCase
from evals.classification.run import main

TEXT = "gasté 3500 en el súper con Mercado Pago"
REQUEST = ClassificationRequest(
    text=TEXT,
    accounts=("Galicia pesos", "Mercado Pago", "Efectivo"),
    expense_categories=("Supermercado", "Transporte"),
    income_categories=("Sueldo",),
    today=date(2026, 11, 17),
)
EXPECTED: dict[str, object] = {
    "message_class": "registration",
    "registration_type": "expense",
    "amount": Decimal("3500"),
    "account": "Mercado Pago",
    "category": "Supermercado",
}
CASE = RegressionCase(name="súper con MP", request=REQUEST, expected=EXPECTED)
RIGHT = Classification(
    message_class=MessageClass.REGISTRATION,
    registration_type=RegistrationType.EXPENSE,
    amount=Decimal("3500"),
    account="Mercado Pago",
    category="Supermercado",
)


def _usage(input_tokens: int = 1000, output_tokens: int = 100) -> ModelUsage:
    return ModelUsage(
        provider="openai",
        model="gpt-5.4-mini",
        prompt_version="classification-15",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


class ScriptedLLM:
    """Gives each answer of its script in turn: a classification, or an error it raises."""

    def __init__(self, script: Sequence[Classification | Exception]) -> None:
        self._script = list(script)
        self.calls = 0

    def classify(self, request: ClassificationRequest) -> Classification:
        answer = self._script[self.calls % len(self._script)]
        self.calls += 1
        if isinstance(answer, Exception):
            raise answer
        if answer.usage is None:
            return replace(answer, usage=_usage())
        return answer


def test_without_run_the_script_only_announces_the_calls_and_their_cost(tmp_path: Path) -> None:
    # Case A1. Every run costs money: nothing is called until the person says so.
    built: list[LLMPort] = []

    def factory() -> LLMPort:
        llm = ScriptedLLM([RIGHT])
        built.append(llm)
        return llm

    out = io.StringIO()
    exit_code = main(
        ["--runs", "5"], cases=(CASE, CASE), llm_factory=factory, out=out, results_dir=tmp_path
    )

    assert exit_code == 0
    assert built == []
    announced = out.getvalue()
    assert "2 casos" in announced
    assert "10 llamadas" in announced
    assert "US$" in announced
    assert list(tmp_path.iterdir()) == []


def test_an_answer_that_matches_everything_expected_is_a_hit_in_each_field() -> None:
    # Case A2, with a field of a movement after the first and how many of them there are.
    case = RegressionCase(
        name="súper y nafta",
        request=REQUEST,
        expected={
            **EXPECTED,
            "more_movements.length": 1,
            "more_movements.0.amount": Decimal("1200"),
        },
    )
    answer = replace(RIGHT, more_movements=(MovementReading(amount=Decimal("1200")),))

    report = run_regression(ScriptedLLM([answer]), (case,), runs=1)

    for field in case.expected:
        assert report.field_rate(field) == (1, 1), field
    assert report.misses == ()


def test_a_field_that_differs_is_a_miss_in_that_field_only_and_the_report_names_it() -> None:
    # Case A3.
    wrong_account = replace(RIGHT, account="Galicia pesos")

    report = run_regression(ScriptedLLM([wrong_account]), (CASE,), runs=1)

    assert report.field_rate("account") == (0, 1)
    assert report.field_rate("amount") == (1, 1)
    [miss] = report.misses
    assert miss.case == "súper con MP"
    assert miss.field == "account"
    assert miss.expected == "Mercado Pago"
    assert miss.got == "Galicia pesos"


def test_a_field_the_case_does_not_name_is_not_compared() -> None:
    # Case A4. The case says nothing of the date: whatever the model says of it is not scored.
    with_a_date = replace(RIGHT, transaction_date=date(2026, 11, 16))

    report = run_regression(ScriptedLLM([with_a_date]), (CASE,), runs=1)

    assert report.field_rate("transaction_date") == (0, 0)
    assert report.misses == ()


def test_each_case_runs_as_many_times_as_asked_and_the_rate_counts_every_run() -> None:
    # Case A5.
    wrong_account = replace(RIGHT, account="Galicia pesos")
    llm = ScriptedLLM([RIGHT, RIGHT, wrong_account, RIGHT, RIGHT])

    report = run_regression(llm, (CASE,), runs=5)

    assert llm.calls == 5
    assert report.field_rate("account") == (4, 5)
    assert report.field_rate("amount") == (5, 5)


def test_an_answer_the_code_would_drop_counts_as_blocked() -> None:
    # Case A6. "MP" is not written in the message: the worker would drop the answer.
    unwritten = replace(RIGHT, account="MP")
    llm = ScriptedLLM([RIGHT, unwritten])

    report = run_regression(llm, (CASE,), runs=2)

    assert report.blocked == 1
    assert report.calls == 2


@pytest.mark.parametrize(
    ("error", "outcome"),
    [
        (ModelRefusedError(_usage()), "refused"),
        (ModelAnswerCutError(_usage()), "truncated"),
        (ModelCallFailedError(LlmOutcome.INVALID_OUTPUT, _usage()), "invalid_output"),
    ],
)
def test_a_call_with_no_answer_counts_by_how_it_ended_and_not_as_a_miss(
    error: Exception, outcome: str
) -> None:
    # Case A7.
    llm = ScriptedLLM([RIGHT, error])

    report = run_regression(llm, (CASE,), runs=2)

    assert report.outcomes[outcome] == 1
    assert report.field_rate("account") == (1, 1)
    assert report.misses == ()


def test_a_provider_error_stops_the_run_and_the_report_says_how_far_it_got() -> None:
    # Case A8. A credit balance used up is an error of the provider: every call after it fails.
    second = replace(CASE, name="segundo")
    failed = ModelCallFailedError(LlmOutcome.PROVIDER_ERROR)
    llm = ScriptedLLM([RIGHT, failed, RIGHT])

    report = run_regression(llm, (CASE, second), runs=1)

    assert llm.calls == 2
    assert report.stopped_at == "segundo"
    assert report.field_rate("account") == (1, 1)


def test_the_tokens_are_added_up_and_the_cost_uses_the_prices_of_the_model() -> None:
    # Case A9. gpt-5.4-mini: US$0.75 a million tokens in, and US$4.50 a million out (ADR 0025).
    first = replace(RIGHT, usage=_usage(input_tokens=2000, output_tokens=300))
    cut = ModelAnswerCutError(_usage(input_tokens=2000, output_tokens=700))

    report = run_regression(ScriptedLLM([first, cut]), (CASE,), runs=2)

    assert report.input_tokens == 4000
    assert report.output_tokens == 1000
    assert report.cost == Decimal("0.0075")
    assert isinstance(report.cost, Decimal)


def test_two_runs_of_different_prompts_show_the_change_by_field_and_the_cases_that_got_worse() -> (
    None
):
    # Case A10.
    other = replace(CASE, name="otro")
    wrong_account = replace(RIGHT, account="Galicia pesos")
    before = run_regression(ScriptedLLM([RIGHT]), (CASE, other), runs=2)
    after = run_regression(
        ScriptedLLM([RIGHT, RIGHT, wrong_account, wrong_account]), (CASE, other), runs=2
    )
    before = replace(before, prompt_version="classification-15")
    after = replace(after, prompt_version="classification-16")

    comparison = compare(after, before)

    assert comparison.field_changes["account"] == ((4, 4), (2, 4))
    assert comparison.field_changes["amount"] == ((4, 4), (4, 4))
    assert comparison.worse_cases == ("otro",)


def _reply_case(text: str, pendings: tuple[NumberedPending, ...]) -> RegressionCase:
    return RegressionCase(
        name=text,
        request=replace(
            REQUEST,
            text=text,
            open_batch=OpenBatch(pendings=pendings, question="¿Con qué cuenta?"),
        ),
        expected={"pending_reply": "continues"},
    )


def _continues(*replies: NumberedReply) -> Classification:
    return Classification(
        message_class=MessageClass.REGISTRATION,
        pending_reply=PendingReply.CONTINUES,
        numbered_replies=replies,
    )


def test_a_reply_by_number_with_an_account_the_message_does_not_write_counts_as_blocked() -> None:
    # Case A11. The fields of the answer itself are empty: what it says goes in each reply.
    pending = {"type": "expense", "amount": "3500", "category": "Supermercado"}
    case = _reply_case(
        "el 1 con Mercado Pago",
        (
            NumberedPending(number=1, interpreted=pending, missing=("account_id",)),
            NumberedPending(number=2, interpreted=pending, missing=("account_id",)),
        ),
    )
    written = _continues(NumberedReply(number=1, reading=MovementReading(account="Mercado Pago")))
    unwritten = _continues(NumberedReply(number=1, reading=MovementReading(account="MP")))
    llm = ScriptedLLM([written, unwritten])

    report = run_regression(llm, (case,), runs=2)

    assert report.blocked == 1


def test_a_reply_is_checked_against_what_its_pending_had_understood() -> None:
    # Case A11. The question offered "Barbería": a yes that brings another name nobody offered
    # nor wrote creates nothing (FEAT-003, CA-45).
    case = _reply_case(
        "sí",
        (
            NumberedPending(
                number=1,
                interpreted={
                    "type": "expense",
                    "amount": "3500",
                    "account": "Mercado Pago",
                    "proposed_category": "Barbería",
                },
                missing=("category_id",),
            ),
        ),
    )
    offered = _continues(
        NumberedReply(
            number=1, reading=MovementReading(proposed_category="Barbería"), accepts_proposal=True
        )
    )
    unoffered = _continues(
        NumberedReply(
            number=1, reading=MovementReading(proposed_category="Peluquería"), accepts_proposal=True
        )
    )
    llm = ScriptedLLM([offered, unoffered])

    report = run_regression(llm, (case,), runs=2)

    assert report.blocked == 1
