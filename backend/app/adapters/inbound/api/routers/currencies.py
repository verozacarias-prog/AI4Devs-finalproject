"""The currencies of the catalog (docs/04-api.md)."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.errors import documented_errors
from app.adapters.inbound.api.request_logging import identify_user
from app.adapters.inbound.api.routers.session import SessionToken
from app.adapters.inbound.api.routes import CURRENCIES, CURRENCIES_TAG
from app.domain.use_cases.currencies.list_currencies import ListCurrencies
from app.domain.use_cases.sessions.authenticate_session import AuthenticateSession


class CurrencyItem(BaseModel):
    code: str = Field(description=reference.CURRENCY_CODE)
    name: str = Field(description=reference.CURRENCY_NAME)


class CurrencyList(BaseModel):
    currencies: list[CurrencyItem] = Field(description=reference.CURRENCIES_LIST)


def build_currencies_router(
    authenticate_session: Callable[[], AuthenticateSession],
    list_currencies: Callable[[], ListCurrencies],
) -> APIRouter:
    router = APIRouter(tags=[CURRENCIES_TAG])

    @router.get(
        CURRENCIES,
        summary=reference.CURRENCIES_SUMMARY,
        description=reference.CURRENCIES_DESCRIPTION,
        response_description=reference.CURRENCIES_OK,
        responses=documented_errors({status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION}),
    )
    def currencies(request: Request, token: SessionToken) -> CurrencyList:
        user = authenticate_session().execute(token)
        identify_user(request, user.id)
        return CurrencyList(
            currencies=[
                CurrencyItem(code=currency.code, name=currency.name)
                for currency in list_currencies().execute()
            ]
        )

    return router
