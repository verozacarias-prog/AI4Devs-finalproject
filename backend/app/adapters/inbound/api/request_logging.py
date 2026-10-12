"""Gives every API request an identifier and logs one line when it ends."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status

from app.adapters.outbound.observability.events import Event, Field, LoggerName
from app.adapters.outbound.observability.logs import request_id_var
from app.constants import MILLISECONDS_PER_SECOND

logger = logging.getLogger(LoggerName.API)


async def log_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Not reset afterwards: whatever the server logs about this request once it leaves this
    # function, such as an unhandled error, carries the same identifier.
    request_id_var.set(uuid.uuid4().hex)
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as error:
        logger.error(
            Event.HTTP_REQUEST,
            extra={
                Field.RESULT: status.HTTP_500_INTERNAL_SERVER_ERROR,
                Field.DURATION_MS: _elapsed_ms(started),
                Field.ERROR_TYPE: type(error).__name__,
            },
        )
        raise
    logger.info(
        Event.HTTP_REQUEST,
        extra={Field.RESULT: response.status_code, Field.DURATION_MS: _elapsed_ms(started)},
    )
    return response


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * MILLISECONDS_PER_SECOND)
