"""When a budget period ends (domain rules, § 3)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from app.domain.entities.budget_period import PeriodType
from app.domain.errors import ErrorCode, InvalidError

_FIRST_FORTNIGHT_START = 1
_SECOND_FORTNIGHT_START = 16
_FIRST_FORTNIGHT_LAST_DAY = 15


def period_end(period_type: PeriodType, period_start: date, indicated_end: date | None) -> date:
    """When a period ends, by its cadence. A custom one ends on the day the user gave. A monthly
    one ends the day before the same day of the next month, a day taken to the last of the month
    when the month lacks it, as in the recurring rules: one that starts on 31 January ends on 27
    February. A biweekly one is the fortnight of the calendar."""
    if period_type is PeriodType.CUSTOM:
        if indicated_end is None:
            raise InvalidError(ErrorCode.PERIOD_END_REQUIRED)
        return indicated_end
    if period_type is PeriodType.BIWEEKLY:
        return _fortnight_end(period_start)
    year, month = divmod(period_start.month, 12)
    next_year, next_month = period_start.year + year, month + 1
    last_day = calendar.monthrange(next_year, next_month)[1]
    same_day = date(next_year, next_month, min(period_start.day, last_day))
    return same_day - timedelta(days=1)


def _fortnight_end(period_start: date) -> date:
    if period_start.day == _FIRST_FORTNIGHT_START:
        return period_start.replace(day=_FIRST_FORTNIGHT_LAST_DAY)
    if period_start.day == _SECOND_FORTNIGHT_START:
        last_day = calendar.monthrange(period_start.year, period_start.month)[1]
        return period_start.replace(day=last_day)
    raise InvalidError(ErrorCode.BIWEEKLY_START_INVALID)


def checked_period_end(
    period_type: PeriodType, period_start: date, indicated_end: date | None
) -> date:
    """The end of a period that is about to be saved: it does not end before it starts, and an
    end that was given has to be the one of its cadence (domain rules, § 3)."""
    end = period_end(period_type, period_start, indicated_end)
    if indicated_end is not None and indicated_end < period_start:
        raise InvalidError(ErrorCode.PERIOD_DATES_INVERTED)
    if indicated_end is not None and indicated_end != end:
        raise InvalidError(ErrorCode.PERIOD_END_NOT_MATCHING)
    return end
