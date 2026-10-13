"""The single place where the API turns an error into an answer, and logs it (ADR 0001).

Every error body has the same shape: its code, plus the fields its endpoint documents. It
never repeats what the client sent and never describes the failure (docs/04-api.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.routes import ERROR_KEY, REQUEST_ID_HEADER, ApiErrorCode
from app.adapters.inbound.api.security_headers import security_headers_for
from app.adapters.outbound.observability.errors import log_error
from app.adapters.outbound.observability.logs import request_id_var
from app.constants import Environment
from app.domain.errors import DomainError, ErrorCategory

STATUS_BY_CATEGORY = {
    ErrorCategory.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCategory.UNAUTHENTICATED: status.HTTP_401_UNAUTHORIZED,
    ErrorCategory.FORBIDDEN: status.HTTP_403_FORBIDDEN,
    ErrorCategory.CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCategory.INVALID: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


class ErrorBody(BaseModel):
    """The body of every error. An endpoint adds a field only when the client needs it."""

    error: str = Field(description=reference.ERROR_CODE)


def documented_errors(errors: Mapping[int, str]) -> dict[int | str, dict[str, object]]:
    """The error responses of an operation, for the reference: when each one happens."""
    return {
        status_code: {"model": ErrorBody, "description": description}
        for status_code, description in errors.items()
    }


def answer_for_status(status_code: int, headers: Mapping[str, str] | None = None) -> Response:
    """What the API answers before any use case ran. The name of the status is its code:
    `not_found`, `method_not_allowed`, `forbidden`."""
    return JSONResponse(
        {ERROR_KEY: HTTPStatus(status_code).name.lower()},
        status_code=status_code,
        headers=headers,
    )


def install_error_handlers(app: FastAPI, environment: Environment) -> None:
    in_full = environment is Environment.LOCAL

    async def expected(request: Request, error: Exception) -> Response:
        assert isinstance(error, DomainError)  # noqa: S101
        log_error(error, in_full=in_full)
        return JSONResponse(
            # The code goes last: no detail can take its place.
            {**error.details, ERROR_KEY: error.code},
            status_code=STATUS_BY_CATEGORY[error.category],
        )

    async def outside_the_contract(request: Request, error: Exception) -> Response:
        """It never reached a use case either, so it leaves no error line."""
        return JSONResponse(
            {ERROR_KEY: ApiErrorCode.INVALID_REQUEST},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def before_any_use_case(request: Request, error: Exception) -> Response:
        """A route that does not exist, a method it does not accept. It leaves no error line:
        nothing in the code to locate, and the line of its request already says the result."""
        assert isinstance(error, HTTPException)  # noqa: S101
        return answer_for_status(error.status_code, error.headers)

    async def unexpected(request: Request, error: Exception) -> Response:
        """It never passes through the middlewares, so it carries their headers itself."""
        log_error(error, in_full=in_full)
        headers = security_headers_for(request.url.path)
        request_id = request_id_var.get()
        if request_id is not None:
            headers = headers | {REQUEST_ID_HEADER: request_id}
        return JSONResponse(
            {ERROR_KEY: ApiErrorCode.INTERNAL_ERROR},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers=headers,
        )

    app.add_exception_handler(DomainError, expected)
    app.add_exception_handler(RequestValidationError, outside_the_contract)
    app.add_exception_handler(HTTPException, before_any_use_case)
    app.add_exception_handler(Exception, unexpected)
