"""When a budget period ends (domain rules, § 3)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from app.domain.entities.budget_period import PeriodType
from app.domain.errors import ErrorCode, InvalidError


def period_end(period_type: PeriodType, period_start: date, indicated_end: date | None) -> date:
    """The end the user gave, or for a monthly period without one, the day before the same day
    of the next month. That day is taken to the last of the month when the month lacks it, as
    in the recurring rules: one that starts on 31 January ends on 27 February."""
    if indicated_end is not None:
        return indicated_end
    if period_type is not PeriodType.MONTHLY:
        # A biweekly end is never computed: the user has to give it.
        raise InvalidError(ErrorCode.PERIOD_END_REQUIRED)
    year, month = divmod(period_start.month, 12)
    next_year, next_month = period_start.year + year, month + 1
    last_day = calendar.monthrange(next_year, next_month)[1]
    same_day = date(next_year, next_month, min(period_start.day, last_day))
    return same_day - timedelta(days=1)


def checked_period_end(
    period_type: PeriodType, period_start: date, indicated_end: date | None
) -> date:
    """The end of a period that is about to be saved: it does not end before it starts."""
    end = period_end(period_type, period_start, indicated_end)
    if end < period_start:
        raise InvalidError(ErrorCode.PERIOD_DATES_INVERTED)
    return end
