"""Who reads and who edits a budget period (domain rules, § 3 and § 10)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date

from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.family_group import GroupRole, Membership
from app.domain.services.dates.local_date import local_today


def _membership_of(period: BudgetPeriod, memberships: Iterable[Membership]) -> Membership | None:
    return next((m for m in memberships if m.family_group_id == period.family_group_id), None)


def can_read(
    period: BudgetPeriod, user_id: uuid.UUID, memberships: Iterable[Membership], time_zone: str
) -> bool:
    """An individual period, only its owner. A group one, its current members, and who left
    only if the period overlaps the days of their membership, in their time zone."""
    if period.family_group_id is None:
        return period.user_id == user_id
    membership = _membership_of(period, memberships)
    if membership is None or membership.user_id != user_id:
        return False
    if membership.left_at is None:
        return True
    joined = local_today(membership.joined_at, time_zone)
    left = local_today(membership.left_at, time_zone)
    return period.period_start <= left and period.period_end >= joined


def can_edit(period: BudgetPeriod, user_id: uuid.UUID, memberships: Iterable[Membership]) -> bool:
    """Its own individual period, or a group one if the user is its current owner."""
    if period.family_group_id is None:
        return period.user_id == user_id
    membership = _membership_of(period, memberships)
    return (
        membership is not None
        and membership.user_id == user_id
        and membership.left_at is None
        and membership.role is GroupRole.OWNER
    )


def covers(period: BudgetPeriod, day: date) -> bool:
    return period.period_start <= day <= period.period_end
