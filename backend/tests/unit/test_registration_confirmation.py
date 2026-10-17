"""The confirmation of a registered movement (FEAT-003, docs/features/FEAT-003/spec.md).

Cases C1-03 and C1-04: it says what was registered and lists what was assumed, together with
the budget it went to (domain rules, § 1).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType
from app.domain.entities.transaction import TransactionType
from app.domain.registration_confirmation import confirmation_text
from tests.support.registration_data import OCTOBER_1, OCTOBER_17, OCTOBER_31

LUCIAS_OCTOBER = BudgetPeriod(
    id=uuid.uuid4(),
    user_id=uuid.uuid4(),
    family_group_id=None,
    period_type=PeriodType.MONTHLY,
    period_start=OCTOBER_1,
    period_end=OCTOBER_31,
    primary_currency="ARS",
    estimated_income=Decimal("0"),
    status=PeriodStatus.CONFIRMED,
)


def test_the_confirmation_of_an_expense_lists_what_was_assumed() -> None:
    # Case C1-03.
    text = confirmation_text(
        type=TransactionType.EXPENSE,
        amount=Decimal("3500.00"),
        currency="ARS",
        account_name="Mercado Pago",
        category_name="Supermercado",
        transaction_date=OCTOBER_17,
        period=LUCIAS_OCTOBER,
    )

    assert text.splitlines() == [
        "¡Listo! Anoté un gasto de $3.500 en Mercado Pago.",
        "Fecha: 17/10/2026",
        "Moneda: ARS",
        "Categoría: Supermercado",
        "Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026",
    ]


def test_the_confirmation_of_an_income_says_it_is_an_income() -> None:
    # Case C1-04.
    text = confirmation_text(
        type=TransactionType.INCOME,
        amount=Decimal("850000.00"),
        currency="ARS",
        account_name="Galicia pesos",
        category_name="Sueldo",
        transaction_date=OCTOBER_17,
        period=LUCIAS_OCTOBER,
    )

    assert text.splitlines() == [
        "¡Listo! Anoté un ingreso de $850.000 en Galicia pesos.",
        "Fecha: 17/10/2026",
        "Moneda: ARS",
        "Categoría: Sueldo",
        "Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026",
    ]
