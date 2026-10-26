"""Reading the budget of the user of the session: periods, summaries and limits (docs/04-api.md)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Request, status
from pydantic import BaseModel, Field

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.errors import documented_errors
from app.adapters.inbound.api.exact_json import ExactAmount, ExactJSONResponse
from app.adapters.inbound.api.request_logging import identify_user
from app.adapters.inbound.api.routers.session import SessionToken
from app.adapters.inbound.api.routes import (
    BUDGET,
    BUDGET_PERIOD_SUMMARY,
    BUDGET_PERIODS,
    BUDGETS_TAG,
)
from app.domain.entities.budget_period import PeriodStatus, PeriodType
from app.domain.entities.transaction import TransactionSource, TransactionType
from app.domain.use_cases.budgets.get_budget_status import GetBudgetStatus
from app.domain.use_cases.budgets.get_period_summary import GetPeriodSummary
from app.domain.use_cases.budgets.list_budget_periods import ListBudgetPeriods
from app.domain.use_cases.sessions.authenticate_session import AuthenticateSession


class BudgetLimitItem(BaseModel):
    id: uuid.UUID = Field(description=reference.BUDGET_ID)
    category_id: uuid.UUID = Field(description=reference.BUDGET_CATEGORY_ID)
    category: str = Field(description=reference.BUDGET_CATEGORY)
    limit_amount: ExactAmount = Field(description=reference.BUDGET_LIMIT)


class BudgetPeriodItem(BaseModel):
    id: uuid.UUID = Field(description=reference.PERIOD_ID)
    family_group_id: uuid.UUID | None = Field(description=reference.PERIOD_GROUP_ID)
    family_group_name: str | None = Field(description=reference.PERIOD_GROUP_NAME)
    period_type: PeriodType = Field(description=reference.PERIOD_TYPE)
    period_start: date = Field(description=reference.PERIOD_START)
    period_end: date = Field(description=reference.PERIOD_END)
    status: PeriodStatus = Field(description=reference.PERIOD_STATUS)
    primary_currency: str = Field(description=reference.PERIOD_CURRENCY)
    estimated_income: ExactAmount = Field(description=reference.PERIOD_ESTIMATED_INCOME)
    can_edit: bool = Field(description=reference.PERIOD_CAN_EDIT)
    is_current: bool = Field(description=reference.PERIOD_IS_CURRENT)
    budgets: list[BudgetLimitItem] = Field(description=reference.PERIOD_BUDGETS)


class BudgetPeriodList(BaseModel):
    budget_periods: list[BudgetPeriodItem] = Field(description=reference.BUDGET_PERIODS_LIST)


class CategorySpendingItem(BaseModel):
    category: str = Field(description=reference.BUDGET_CATEGORY)
    budget_id: uuid.UUID | None = Field(description=reference.SPENDING_BUDGET_ID)
    limit_amount: ExactAmount | None = Field(description=reference.SPENDING_LIMIT)
    spent_amount: ExactAmount = Field(description=reference.SPENT_AMOUNT)
    used_percentage: ExactAmount | None = Field(description=reference.USED_PERCENTAGE)


class PeriodSummaryBody(BaseModel):
    budget_period_id: uuid.UUID = Field(description=reference.PERIOD_ID)
    primary_currency: str = Field(description=reference.PERIOD_CURRENCY)
    estimated_income: ExactAmount = Field(description=reference.PERIOD_ESTIMATED_INCOME)
    actual_income: ExactAmount = Field(description=reference.PERIOD_ACTUAL_INCOME)
    total_spent: ExactAmount = Field(description=reference.PERIOD_TOTAL_SPENT)
    categories: list[CategorySpendingItem] = Field(description=reference.PERIOD_CATEGORIES)


class BudgetMovementItem(BaseModel):
    id: uuid.UUID = Field(description=reference.MOVEMENT_ID)
    transaction_date: date = Field(description=reference.MOVEMENT_DATE)
    description: str | None = Field(description=reference.MOVEMENT_DESCRIPTION)
    type: TransactionType = Field(description=reference.MOVEMENT_TYPE)
    amount: ExactAmount = Field(description=reference.MOVEMENT_AMOUNT)
    currency: str = Field(description=reference.MOVEMENT_CURRENCY)
    budget_amount: ExactAmount = Field(description=reference.MOVEMENT_BUDGET_AMOUNT)
    exchange_rate: ExactAmount | None = Field(description=reference.MOVEMENT_EXCHANGE_RATE)
    account: str = Field(description=reference.MOVEMENT_ACCOUNT)
    source: TransactionSource = Field(description=reference.MOVEMENT_SOURCE)


class BudgetStatusBody(BaseModel):
    id: uuid.UUID = Field(description=reference.BUDGET_ID)
    budget_period_id: uuid.UUID = Field(description=reference.BUDGET_PERIOD_ID)
    category: str = Field(description=reference.BUDGET_CATEGORY)
    primary_currency: str = Field(description=reference.PERIOD_CURRENCY)
    limit_amount: ExactAmount = Field(description=reference.BUDGET_LIMIT)
    spent_amount: ExactAmount = Field(description=reference.SPENT_AMOUNT)
    used_percentage: ExactAmount = Field(description=reference.USED_PERCENTAGE)
    transactions: list[BudgetMovementItem] = Field(description=reference.BUDGET_TRANSACTIONS)


def build_budgets_router(
    authenticate_session: Callable[[], AuthenticateSession],
    list_budget_periods: Callable[[], ListBudgetPeriods],
    get_period_summary: Callable[[], GetPeriodSummary],
    get_budget_status: Callable[[], GetBudgetStatus],
) -> APIRouter:
    router = APIRouter(tags=[BUDGETS_TAG])

    @router.get(
        BUDGET_PERIODS,
        response_model=BudgetPeriodList,
        response_class=ExactJSONResponse,
        summary=reference.BUDGET_PERIODS_SUMMARY,
        description=reference.BUDGET_PERIODS_DESCRIPTION,
        response_description=reference.BUDGET_PERIODS_OK,
        responses=documented_errors({status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION}),
    )
    def budget_periods(request: Request, token: SessionToken) -> ExactJSONResponse:
        user = authenticate_session().execute(token)
        identify_user(request, user.id)
        listed = BudgetPeriodList(
            budget_periods=[
                BudgetPeriodItem(
                    id=item.period.id,
                    family_group_id=item.period.family_group_id,
                    family_group_name=item.family_group_name,
                    period_type=item.period.period_type,
                    period_start=item.period.period_start,
                    period_end=item.period.period_end,
                    status=item.period.status,
                    primary_currency=item.period.primary_currency,
                    estimated_income=item.period.estimated_income,
                    can_edit=item.can_edit,
                    is_current=item.is_current,
                    budgets=[
                        BudgetLimitItem(
                            id=limit.budget.id,
                            category_id=limit.budget.category_id,
                            category=limit.category,
                            limit_amount=limit.budget.limit_amount,
                        )
                        for limit in item.budgets
                    ],
                )
                for item in list_budget_periods().execute(user.id)
            ]
        )
        return ExactJSONResponse(listed.model_dump())

    @router.get(
        BUDGET_PERIOD_SUMMARY,
        response_model=PeriodSummaryBody,
        response_class=ExactJSONResponse,
        summary=reference.PERIOD_SUMMARY_SUMMARY,
        description=reference.PERIOD_SUMMARY_DESCRIPTION,
        response_description=reference.PERIOD_SUMMARY_OK,
        responses=documented_errors(
            {
                status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION,
                status.HTTP_404_NOT_FOUND: reference.PERIOD_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_CONTENT: reference.PERIOD_ID_INVALID,
            }
        ),
    )
    def period_summary(
        request: Request,
        token: SessionToken,
        period_id: Annotated[uuid.UUID, Path(description=reference.PERIOD_ID)],
    ) -> ExactJSONResponse:
        user = authenticate_session().execute(token)
        identify_user(request, user.id)
        summary = get_period_summary().execute(user.id, period_id)
        body = PeriodSummaryBody(
            budget_period_id=summary.period.id,
            primary_currency=summary.period.primary_currency,
            estimated_income=summary.estimated_income,
            actual_income=summary.actual_income,
            total_spent=summary.total_spent,
            categories=[
                CategorySpendingItem(
                    category=item.category,
                    budget_id=item.budget_id,
                    limit_amount=item.limit_amount,
                    spent_amount=item.spent_amount,
                    used_percentage=item.used_percentage,
                )
                for item in summary.categories
            ],
        )
        return ExactJSONResponse(body.model_dump())

    @router.get(
        BUDGET,
        response_model=BudgetStatusBody,
        response_class=ExactJSONResponse,
        summary=reference.BUDGET_STATUS_SUMMARY,
        description=reference.BUDGET_STATUS_DESCRIPTION,
        response_description=reference.BUDGET_STATUS_OK,
        responses=documented_errors(
            {
                status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION,
                status.HTTP_404_NOT_FOUND: reference.BUDGET_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_CONTENT: reference.BUDGET_ID_INVALID,
            }
        ),
    )
    def budget_status(
        request: Request,
        token: SessionToken,
        budget_id: Annotated[uuid.UUID, Path(description=reference.BUDGET_ID)],
    ) -> ExactJSONResponse:
        user = authenticate_session().execute(token)
        identify_user(request, user.id)
        found = get_budget_status().execute(user.id, budget_id)
        body = BudgetStatusBody(
            id=found.budget.id,
            budget_period_id=found.period.id,
            category=found.category,
            primary_currency=found.primary_currency,
            limit_amount=found.limit_amount,
            spent_amount=found.spent_amount,
            used_percentage=found.used_percentage,
            transactions=[
                BudgetMovementItem(
                    id=movement.transaction.id,
                    transaction_date=movement.transaction.transaction_date,
                    description=movement.transaction.description,
                    type=movement.transaction.type,
                    amount=movement.transaction.amount,
                    currency=movement.transaction.currency,
                    budget_amount=movement.budget_amount,
                    exchange_rate=movement.exchange_rate,
                    account=movement.account,
                    source=movement.source,
                )
                for movement in found.movements
            ],
        )
        return ExactJSONResponse(body.model_dump())

    return router
