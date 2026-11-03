"""A draft receives no movements, and a confirmed period does (FEAT-005).

Cases C1-09 and C1-10 of docs/features/FEAT-005/spec.md: the same expense of Lucía is resolved
against the only period that covers its day, first in draft and then confirmed (domain rules,
§ 1 and § 3).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus
from app.domain.entities.transaction import TransactionType
from app.domain.services.transactions.movement_resolution import (
    Interpretation,
    Missing,
    MissingField,
    ResolvedMovement,
    resolve,
)
from tests.support.budget_data import BUENOS_AIRES, PESOS, SUPERMARKET, LuciaBudget, lucia_budget

NOVEMBER_15 = date(2026, 11, 15)


def _expense_on_the_fifteenth() -> Interpretation:
    return Interpretation(
        type=TransactionType.EXPENSE,
        amount=Decimal("5000.00"),
        account="Galicia pesos",
        account_mention="galicia pesos",
        category=SUPERMARKET,
        proposed_category=None,
        transaction_date=NOVEMBER_15,
    )


def _november(budget: LuciaBudget, status: PeriodStatus) -> BudgetPeriod:
    return replace(
        budget.period,
        period_start=date(2026, 11, 10),
        period_end=date(2026, 12, 9),
        status=status,
    )


def test_an_expense_that_falls_only_in_a_draft_stays_pending() -> None:
    # Case C1-09.
    budget = lucia_budget()
    draft = _november(budget, PeriodStatus.DRAFT)

    resolution = resolve(
        _expense_on_the_fifteenth(),
        [budget.pesos],
        list(budget.categories.values()),
        [draft],
        BUENOS_AIRES,
        PESOS,
    )

    assert isinstance(resolution, Missing)
    assert resolution.fields == (MissingField.PERIOD,)


def test_the_same_expense_with_the_period_confirmed_is_charged_without_asking() -> None:
    # Case C1-10.
    budget = lucia_budget()
    confirmed = _november(budget, PeriodStatus.CONFIRMED)

    resolution = resolve(
        _expense_on_the_fifteenth(),
        [budget.pesos],
        list(budget.categories.values()),
        [confirmed],
        BUENOS_AIRES,
        PESOS,
    )

    assert isinstance(resolution, ResolvedMovement)
    assert resolution.period == confirmed
