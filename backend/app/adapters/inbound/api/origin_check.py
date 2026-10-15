"""Refuses a request that changes something unless the page of the API itself sent it (ADR 0016).

Together with the SameSite cookie, this is what keeps another site from acting with the
session of a user. The webhook of WhatsApp will be the one exception: it has no cookie and
proves who it is with its signature.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import Request, Response, status
from starlette.routing import Match

from app.adapters.inbound.api.errors import answer_for_status
from app.adapters.inbound.api.routes import (
    CONTENT_TYPE_HEADER,
    HOST_HEADER,
    JSON_CONTENT_TYPE,
    MEDIA_TYPE_PARAMETER_SEPARATOR,
    ORIGIN_HEADER,
    READ_ONLY_METHODS,
)


async def refuse_requests_from_elsewhere(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Decided from the headers alone, before anything the request sent is read. Only a
    # request some route would serve is refused here: the others go on to their own answer,
    # that the route does not exist or does not accept that method.
    if _some_route_would_serve(request) and not _comes_from_the_own_page_as_json(request):
        return answer_for_status(status.HTTP_403_FORBIDDEN)
    return await call_next(request)


def _some_route_would_serve(request: Request) -> bool:
    return any(route.matches(request.scope)[0] is Match.FULL for route in request.app.routes)


def _comes_from_the_own_page_as_json(request: Request) -> bool:
    if request.method in READ_ONLY_METHODS:
        return True
    # A browser always sends Origin with these methods, so a request without it is refused
    # too. The scheme is not compared: behind a proxy the API does not see the one the
    # browser used.
    origin = request.headers.get(ORIGIN_HEADER)
    host = request.headers.get(HOST_HEADER)
    if not origin or not host or urlsplit(origin).netloc != host:
        return False
    content_type = request.headers.get(CONTENT_TYPE_HEADER, "")
    media_type = content_type.split(MEDIA_TYPE_PARAMETER_SEPARATOR)[0].strip().lower()
    return media_type == JSON_CONTENT_TYPE
