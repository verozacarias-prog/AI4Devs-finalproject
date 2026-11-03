"""The development entry: a real session without a login code (docs/04-api.md, ADR 0016).

This router is installed only when the entry is enabled, so turned off its routes do not
exist. The list of users is installed only in the local environment.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Self

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field, model_validator

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.errors import ErrorBody, documented_errors
from app.adapters.inbound.api.routers.session import set_session_cookie
from app.adapters.inbound.api.routes import DEV_SESSION, DEV_TAG, DEV_USERS
from app.adapters.observability.events import Event, LoggerName, SessionMethod
from app.adapters.observability.events import Field as LogField
from app.domain.use_cases.sessions.open_dev_session import OpenDevSession
from app.domain.use_cases.test_data.list_test_users import ListTestUsers

logger = logging.getLogger(LoggerName.API)


class DevUser(BaseModel):
    id: uuid.UUID = Field(description=reference.USER_ID)
    name: str = Field(description=reference.USER_NAME)


class DevUsers(BaseModel):
    users: list[DevUser] = Field(description=reference.DEV_USERS_LIST)


class DevSessionRequest(BaseModel):
    user_id: uuid.UUID | None = Field(default=None, description=reference.DEV_SESSION_USER_ID)
    access_token: str | None = Field(default=None, description=reference.DEV_SESSION_ACCESS_TOKEN)
    accept_test_notice: str | None = Field(
        default=None, description=reference.DEV_SESSION_ACCEPT_TEST_NOTICE
    )

    @model_validator(mode="after")
    def _names_who_enters(self) -> Self:
        if self.user_id is None and self.access_token is None:
            raise ValueError
        return self


class TestNoticeRequired(ErrorBody):
    __test__ = False  # not a test class, whatever its name suggests to pytest

    notice_version: str = Field(description=reference.DEV_SESSION_NOTICE_VERSION)


def build_dev_entry_router(
    open_dev_session: Callable[[], OpenDevSession],
    list_test_users: Callable[[], ListTestUsers] | None,
) -> APIRouter:
    router = APIRouter(tags=[DEV_TAG])

    if list_test_users is not None:

        @router.get(
            DEV_USERS,
            summary=reference.DEV_USERS_SUMMARY,
            description=reference.DEV_USERS_DESCRIPTION,
            response_description=reference.DEV_USERS_OK,
            responses=documented_errors({status.HTTP_404_NOT_FOUND: reference.DEV_USERS_NOT_FOUND}),
        )
        def users() -> DevUsers:
            return DevUsers(
                users=[DevUser(id=user.id, name=user.name) for user in list_test_users().execute()]
            )

    @router.post(
        DEV_SESSION,
        status_code=status.HTTP_204_NO_CONTENT,
        summary=reference.DEV_SESSION_SUMMARY,
        description=reference.DEV_SESSION_DESCRIPTION,
        response_description=reference.DEV_SESSION_OK,
        responses=documented_errors(
            {
                status.HTTP_403_FORBIDDEN: reference.FOREIGN_REQUEST,
                status.HTTP_413_CONTENT_TOO_LARGE: reference.BODY_TOO_LARGE,
                status.HTTP_404_NOT_FOUND: reference.DEV_SESSION_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_CONTENT: reference.DEV_SESSION_INVALID,
            }
        )
        | {
            status.HTTP_409_CONFLICT: {
                "model": TestNoticeRequired,
                "description": reference.DEV_SESSION_NOTICE_REQUIRED,
            }
        },
    )
    def enter(body: DevSessionRequest) -> Response:
        opened = open_dev_session().execute(
            user_id=body.user_id,
            access_token=body.access_token,
            accept_test_notice=body.accept_test_notice,
        )
        logger.info(
            Event.AUTH_SESSION_CREATED,
            extra={
                LogField.USER_ID: str(opened.session.user_id),
                LogField.SESSION_ID: str(opened.session.id),
                LogField.METHOD: (
                    SessionMethod.DEV_USER_LIST
                    if body.user_id is not None
                    else SessionMethod.DEV_PERSONAL_LINK
                ),
            },
        )
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        set_session_cookie(response, opened.token)
        return response

    return router
