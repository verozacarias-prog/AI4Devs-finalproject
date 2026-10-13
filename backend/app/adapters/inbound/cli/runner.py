"""Runs an operation command: the single place where a command turns an error into its output.

A command only does its work and returns what to tell whoever ran it. Settings, logging, the
reference of the run, the message of an error and the exit code are decided here (ADR 0001).
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Callable, Mapping
from typing import TextIO

from app import messages
from app.adapters.outbound.observability.errors import log_error
from app.adapters.outbound.observability.logs import configure_logging, request_id_var
from app.constants import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_REFUSED,
    LINE_END,
    Environment,
    ProcessName,
)
from app.domain.errors import DomainError
from app.settings import Settings, SettingsError, load_settings


def run_command(
    command: Callable[[Settings], str],
    environ: Mapping[str, str],
    out: TextIO,
    log_stream: TextIO | None = None,
) -> int:
    try:
        settings = load_settings(environ)
    except SettingsError as error:
        out.write(str(error) + LINE_END)
        return EXIT_FAILED
    configure_logging(log_stream or sys.stdout, settings.version, ProcessName.CLI)
    # The identifier of this run: every line it logs carries it, and so does its error message.
    reference = uuid.uuid4().hex
    request_id_var.set(reference)
    in_full = settings.environment is Environment.LOCAL
    try:
        out.write(command(settings) + LINE_END)
    except DomainError as error:
        log_error(error, in_full=in_full)
        template = messages.COMMAND_ERRORS.get(error.code, messages.COMMAND_REFUSED)
        context = {name: str(value) for name, value in error.context.items()}
        _write_error(out, template.format(code=error.code, **context), reference)
        return EXIT_REFUSED
    except Exception as error:
        log_error(error, in_full=in_full)
        _write_error(out, messages.COMMAND_FAILED, reference)
        return EXIT_FAILED
    return EXIT_OK


def _write_error(out: TextIO, message: str, reference: str) -> None:
    out.write(message + LINE_END)
    out.write(messages.ERROR_REFERENCE.format(reference=reference) + LINE_END)
