"""Refuses a request whose body is over the limit, before it reaches the memory (docs/04-api.md).

A body that declares its size is refused from the headers alone, before the origin check and
without reading it. One that does not declare it is counted as it is read, which happens after
that check (ADR 0016), and refused as soon as it goes over.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response, status
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.adapters.inbound.api.errors import answer_for_status
from app.adapters.inbound.api.routes import CONTENT_LENGTH_HEADER
from app.constants import MAX_REQUEST_BODY_BYTES

_LEADING_ZERO = "0"
_DIGITS_OF_THE_LIMIT = len(str(MAX_REQUEST_BODY_BYTES))


async def refuse_declared_bodies_over_the_limit(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    declared = request.headers.get(CONTENT_LENGTH_HEADER, "").lstrip(_LEADING_ZERO)
    # The digits come first: Python refuses to turn a very long string into a number.
    if declared.isdecimal() and (
        len(declared) > _DIGITS_OF_THE_LIMIT or int(declared) > MAX_REQUEST_BODY_BYTES
    ):
        return answer_for_status(status.HTTP_413_CONTENT_TOO_LARGE)
    return await call_next(request)


class CountedBody:
    """A plain ASGI middleware, the one kind that sees a body while the route reads it.

    It has to run after the middlewares written as functions: an error that crosses one of them
    comes out wrapped, and the route would answer it as a 400.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        read = 0

        async def counted() -> Message:
            nonlocal read
            message = await receive()
            read += len(message.get("body", b""))
            if read > MAX_REQUEST_BODY_BYTES:
                # The handler of the errors the server answers on its own turns it into the body.
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE)
            return message

        await self._app(scope, counted, send)
