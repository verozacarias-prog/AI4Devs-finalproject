from __future__ import annotations

import uuid

from app import test_data
from app.domain.entities.account import Account
from app.domain.entities.budget_period import first_period
from app.domain.entities.financial_profile import FinancialProfile
from app.domain.entities.user import OnboardingStatus, User
from app.domain.local_date import local_today
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


class CreateTestUser:
    """Creates a test user from the template: accounts, first period and profile, all invented.

    It writes inside the transaction it is given and leaves the commit to its caller. Only the
    test data script and the acceptance of the test notice call it (ADR 0016).
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def execute(
        self, unit_of_work: UnitOfWorkPort, *, name: str, phone: str, terms_version: str
    ) -> User:
        now = self._clock.now()
        user = User(
            id=uuid.uuid4(),
            name=name,
            whatsapp_phone=phone,
            country=test_data.TEMPLATE_COUNTRY,
            time_zone=test_data.TEMPLATE_TIME_ZONE,
            primary_currency=test_data.TEMPLATE_CURRENCY,
            exchange_rate_reference=test_data.TEMPLATE_EXCHANGE_RATE_REFERENCE,
            terms_accepted_at=now,
            terms_version=terms_version,
            notifications_opt_in=test_data.TEMPLATE_NOTIFICATIONS_OPT_IN,
            onboarding_status=OnboardingStatus.COMPLETED,
        )
        unit_of_work.users.add(user)
        for account in test_data.TEMPLATE_ACCOUNTS:
            unit_of_work.accounts.add(
                Account(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    name=account.name,
                    type=account.type,
                    currency=account.currency,
                    initial_balance=account.initial_balance,
                    opened_at=now,
                )
            )
        today = local_today(now, user.time_zone)
        unit_of_work.budget_periods.add(
            first_period(user_id=user.id, currency=user.primary_currency, today=today)
        )
        unit_of_work.financial_profiles.add(
            FinancialProfile(
                user_id=user.id,
                income_range=test_data.TEMPLATE_INCOME_RANGE,
                dependents=test_data.TEMPLATE_DEPENDENTS,
                has_debts=test_data.TEMPLATE_HAS_DEBTS,
                emergency_fund_months=test_data.TEMPLATE_EMERGENCY_FUND_MONTHS,
                main_goal=test_data.TEMPLATE_MAIN_GOAL,
            )
        )
        return user
