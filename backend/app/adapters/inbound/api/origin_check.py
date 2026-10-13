"""Refuses a request that changes something unless the page of the API itself sent it (ADR 0016).

Together with the SameSite cookie, this is what keeps another site from acting with the
session of a user. The webhook of WhatsApp will be the one exception: it has no cookie and
proves who it is with its signature.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status

from app.adapters.inbound.api.routes import (
    CONTENT_TYPE_HEADER,
    HOST_HEADER,
    JSON_CONTENT_TYPE,
    MEDIA_TYPE_PARAMETER_SEPARATOR,
    ORIGIN_HEADER,
    READ_ONLY_METHODS,
)


def require_own_origin_and_json(request: Request) -> None:
    if request.method in READ_ONLY_METHODS:
        return
    # A browser always sends Origin with these methods, so a request without it is refused
    # too. The scheme is not compared: behind a proxy the API does not see the one the
    # browser used.
    origin = request.headers.get(ORIGIN_HEADER)
    host = request.headers.get(HOST_HEADER)
    if not origin or not host or urlsplit(origin).netloc != host:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    content_type = request.headers.get(CONTENT_TYPE_HEADER, "")
    media_type = content_type.split(MEDIA_TYPE_PARAMETER_SEPARATOR)[0].strip().lower()
    if media_type != JSON_CONTENT_TYPE:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
