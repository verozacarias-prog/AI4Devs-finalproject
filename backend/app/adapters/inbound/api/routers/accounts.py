"""The accounts of the user of the session, with their computed balance (docs/04-api.md)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, status
from pydantic import BaseModel, Field, WithJsonSchema

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.errors import documented_errors
from app.adapters.inbound.api.exact_json import ExactJSONResponse
from app.adapters.inbound.api.routers.session import SessionToken
from app.adapters.inbound.api.routes import ACCOUNTS, ACCOUNTS_TAG
from app.domain.entities.account import AccountType, BalanceKind
from app.domain.use_cases.accounts.list_accounts import ListAccounts
from app.domain.use_cases.sessions.authenticate_session import AuthenticateSession

# An amount travels as a JSON number with its exact digits, never as a string.
ExactAmount = Annotated[Decimal, WithJsonSchema({"type": "number"})]


class AccountItem(BaseModel):
    id: uuid.UUID = Field(description=reference.ACCOUNT_ID)
    name: str = Field(description=reference.ACCOUNT_NAME)
    type: AccountType = Field(description=reference.ACCOUNT_TYPE)
    currency: str = Field(description=reference.ACCOUNT_CURRENCY)
    balance: ExactAmount = Field(description=reference.ACCOUNT_BALANCE)
    balance_kind: BalanceKind = Field(description=reference.ACCOUNT_BALANCE_KIND)


class AccountList(BaseModel):
    accounts: list[AccountItem] = Field(description=reference.ACCOUNTS_LIST)


def build_accounts_router(
    authenticate_session: Callable[[], AuthenticateSession],
    list_accounts: Callable[[], ListAccounts],
) -> APIRouter:
    router = APIRouter(tags=[ACCOUNTS_TAG])

    @router.get(
        ACCOUNTS,
        response_model=AccountList,
        response_class=ExactJSONResponse,
        summary=reference.ACCOUNTS_SUMMARY,
        description=reference.ACCOUNTS_DESCRIPTION,
        response_description=reference.ACCOUNTS_OK,
        responses=documented_errors({status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION}),
    )
    def accounts(token: SessionToken) -> ExactJSONResponse:
        user = authenticate_session().execute(token)
        listed = AccountList(
            accounts=[
                AccountItem(
                    id=item.account.id,
                    name=item.account.name,
                    type=item.account.type,
                    currency=item.account.currency,
                    balance=item.balance,
                    balance_kind=item.balance_kind,
                )
                for item in list_accounts().execute(user.id)
            ]
        )
        return ExactJSONResponse(listed.model_dump())

    return router
