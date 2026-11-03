"""When a budget period ends (FEAT-005, docs/features/FEAT-005/spec.md).

Cases C1-01 to C1-04, C1-19 and C2-12, the unit ones about the end of a period: a monthly one
ends the day before the same day of the next month, taken to the last day of that month when it
does not have it; a biweekly one ends on the 15th or on the last day of the month; a custom one
ends on the day given, and without it has no end (domain rules, § 3).
"""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.entities.budget_period import PeriodType
from app.domain.errors import DomainError
from app.domain.services.budgets.period_dates import period_end


def test_a_monthly_one_ends_the_day_before_the_same_day_of_the_next_month() -> None:
    # Case C1-01.
    assert period_end(PeriodType.MONTHLY, date(2026, 11, 10), None) == date(2026, 12, 9)


def test_a_monthly_one_that_starts_on_the_first_ends_on_the_last_day_of_the_month() -> None:
    # Case C1-02: the day before 1 March.
    assert period_end(PeriodType.MONTHLY, date(2027, 2, 1), None) == date(2027, 2, 28)


def test_a_monthly_one_that_starts_on_a_day_the_next_month_does_not_have() -> None:
    # Case C1-03: 31 February does not exist, so the same day of the next month is the 28th,
    # and the period ends the day before.
    assert period_end(PeriodType.MONTHLY, date(2027, 1, 31), None) == date(2027, 2, 27)


def test_a_custom_one_ends_on_the_day_given() -> None:
    # Case C1-04: it lasts 21 days, the transition period.
    indicated = date(2026, 11, 30)

    assert period_end(PeriodType.CUSTOM, date(2026, 11, 10), indicated) == indicated


def test_a_biweekly_one_ends_on_the_15th_or_on_the_last_day_of_the_month() -> None:
    # Case C1-19.
    assert period_end(PeriodType.BIWEEKLY, date(2026, 11, 1), None) == date(2026, 11, 15)
    assert period_end(PeriodType.BIWEEKLY, date(2027, 2, 16), None) == date(2027, 2, 28)


def test_a_custom_period_without_an_end_has_no_end() -> None:
    # Case C2-12.
    with pytest.raises(DomainError) as raised:
        period_end(PeriodType.CUSTOM, date(2026, 11, 10), None)

    assert raised.value.code == "period_end_required"
