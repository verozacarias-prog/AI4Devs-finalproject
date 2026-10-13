"""The session of a request: who is behind it, and closing it (docs/04-api.md).

Every endpoint that needs the user takes it from here, never from the request itself.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from app.adapters.inbound.api.routes import (
    AUTH_LOGOUT,
    ME,
    SESSION_COOKIE,
    SESSION_COOKIE_PATH,
    SESSION_COOKIE_SAME_SITE,
    SESSION_TAG,
)
from app.domain.use_cases.authenticate_session import AuthenticateSession
from app.domain.use_cases.close_session import CloseSession


class Me(BaseModel):
    id: uuid.UUID
    name: str


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

    @router.get(ME)
    def me(request: Request) -> Me:
        user = authenticate_session().execute(request.cookies.get(SESSION_COOKIE))
        return Me(id=user.id, name=user.name)

    @router.post(AUTH_LOGOUT, status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request) -> Response:
        close_session().execute(request.cookies.get(SESSION_COOKIE))
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        clear_session_cookie(response)
        return response

    return router
