"""The log line an error leaves, the same in every process (docs/operacion.md, 6.3).

It says which error, by which path and on which rows, and never with which values. Each inbound
adapter calls this from the single place where it turns an error into its output.
"""

from __future__ import annotations

import logging
import sys
import sysconfig
import traceback
from pathlib import Path

from app.adapters.outbound.observability.events import MAX_STACK_DEPTH, Event, Field, LoggerName
from app.adapters.outbound.observability.logs import LogValue
from app.domain.errors import DomainError, StoreRejectionError

logger = logging.getLogger(LoggerName.ERRORS)

# Where the interpreter and the installed libraries live. Code anywhere else is the application.
_LIBRARY_DIRECTORIES = tuple({Path(path).resolve() for path in sysconfig.get_paths().values()})


def log_error(error: BaseException, *, in_full: bool, code: str | None = None) -> None:
    """Logs one line for this error. `code` is for an expected error that is not a DomainError.

    `in_full` also writes the message and the traceback to the error output. Only the local
    environment asks for it, because only its users are invented.
    """
    fields: dict[str, LogValue] = {
        Field.ERROR_TYPE: type(error).__name__,
        Field.ERROR_STACK: code_path(error),
    }
    if isinstance(error, DomainError):
        code = error.code
        for name, value in error.context.items():
            fields[name] = str(value)
    if isinstance(error, DomainError | StoreRejectionError):
        if error.constraint is not None:
            fields[Field.CONSTRAINT] = error.constraint
        if error.__cause__ is not None:
            fields[Field.ERROR_CAUSE] = type(error.__cause__).__name__
    if code is None:
        logger.error(Event.ERROR_UNEXPECTED, extra=fields)
    else:
        logger.info(Event.ERROR_EXPECTED, extra={**fields, Field.ERROR_CODE: code})
    if in_full:
        traceback.print_exception(error, file=sys.stderr)


def code_path(error: BaseException) -> list[str]:
    """The steps of the error inside the application, from the entry point to its origin."""
    places: list[str] = []
    step = error.__traceback__
    while step is not None:
        frame = step.tb_frame
        module = frame.f_globals.get("__name__")
        if isinstance(module, str) and _is_application_code(frame.f_code.co_filename):
            places.append(f"{module}:{frame.f_code.co_name}:{step.tb_lineno}")
        step = step.tb_next
    return places[-MAX_STACK_DEPTH:]


def _is_application_code(filename: str) -> bool:
    if filename.startswith("<"):  # frozen or generated code
        return False
    path = Path(filename).resolve()
    return not any(path.is_relative_to(directory) for directory in _LIBRARY_DIRECTORIES)
