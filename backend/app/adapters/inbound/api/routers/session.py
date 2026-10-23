"""The session of a request: who is behind it, and closing it (docs/04-api.md).

Every endpoint that needs the user takes it from here, never from the request itself.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import APIKeyCookie
from pydantic import BaseModel, Field

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.errors import documented_errors
from app.adapters.inbound.api.request_logging import identify_user
from app.adapters.inbound.api.routes import (
    AUTH_LOGOUT,
    ME,
    SESSION_COOKIE,
    SESSION_COOKIE_PATH,
    SESSION_COOKIE_SAME_SITE,
    SESSION_TAG,
)
from app.domain.use_cases.sessions.authenticate_session import AuthenticateSession
from app.domain.use_cases.sessions.close_session import CloseSession

# Reads the token of the session cookie, and tells the reference which operations ask for
# a session. A missing cookie is not refused here: the use case answers for every case.
session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    scheme_name=reference.SESSION_COOKIE_SCHEME,
    description=reference.SESSION_COOKIE_DESCRIPTION,
    auto_error=False,
)
SessionToken = Annotated[str | None, Depends(session_cookie)]


class Me(BaseModel):
    id: uuid.UUID = Field(description=reference.USER_ID)
    name: str = Field(description=reference.USER_NAME)


def set_session_cookie(response: Response, token: str) -> None:
    # No Domain and no Max-Age: the cookie lives as long as the browser session, and the
    # server decides when the session ends.
    response.set_cookie(
        SESSION_COOKIE,
        token,
        path=SESSION_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite=SESSION_COOKIE_SAME_SITE,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        path=SESSION_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite=SESSION_COOKIE_SAME_SITE,
    )


def build_session_router(
    authenticate_session: Callable[[], AuthenticateSession],
    close_session: Callable[[], CloseSession],
) -> APIRouter:
    router = APIRouter(tags=[SESSION_TAG])

    @router.get(
        ME,
        summary=reference.ME_SUMMARY,
        description=reference.ME_DESCRIPTION,
        response_description=reference.ME_OK,
        responses=documented_errors({status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION}),
    )
    def me(request: Request, token: SessionToken) -> Me:
        user = authenticate_session().execute(token)
        identify_user(request, user.id)
        return Me(id=user.id, name=user.name)

    @router.post(
        AUTH_LOGOUT,
        status_code=status.HTTP_204_NO_CONTENT,
        summary=reference.LOGOUT_SUMMARY,
        description=reference.LOGOUT_DESCRIPTION,
        response_description=reference.LOGOUT_OK,
        responses=documented_errors(
            {
                status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION,
                status.HTTP_403_FORBIDDEN: reference.FOREIGN_REQUEST,
            }
        ),
    )
    def logout(request: Request, token: SessionToken) -> Response:
        identify_user(request, close_session().execute(token))
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        clear_session_cookie(response)
        return response

    return router
