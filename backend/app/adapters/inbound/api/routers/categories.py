"""The categories of expenses of the user of the session (docs/04-api.md)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.errors import documented_errors
from app.adapters.inbound.api.request_logging import identify_user
from app.adapters.inbound.api.routers.session import SessionToken
from app.adapters.inbound.api.routes import CATEGORIES, CATEGORIES_TAG
from app.domain.use_cases.categories.list_expense_categories import ListExpenseCategories
from app.domain.use_cases.sessions.authenticate_session import AuthenticateSession


class CategoryItem(BaseModel):
    id: uuid.UUID = Field(description=reference.CATEGORY_ID)
    name: str = Field(description=reference.CATEGORY_NAME)
    is_base: bool = Field(description=reference.CATEGORY_IS_BASE)


class CategoryList(BaseModel):
    categories: list[CategoryItem] = Field(description=reference.CATEGORIES_LIST)


def build_categories_router(
    authenticate_session: Callable[[], AuthenticateSession],
    list_expense_categories: Callable[[], ListExpenseCategories],
) -> APIRouter:
    router = APIRouter(tags=[CATEGORIES_TAG])

    @router.get(
        CATEGORIES,
        summary=reference.CATEGORIES_SUMMARY,
        description=reference.CATEGORIES_DESCRIPTION,
        response_description=reference.CATEGORIES_OK,
        responses=documented_errors({status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION}),
    )
    def categories(request: Request, token: SessionToken) -> CategoryList:
        user = authenticate_session().execute(token)
        identify_user(request, user.id)
        return CategoryList(
            categories=[
                CategoryItem(id=category.id, name=category.name, is_base=category.user_id is None)
                for category in list_expense_categories().execute(user.id)
            ]
        )

    return router
