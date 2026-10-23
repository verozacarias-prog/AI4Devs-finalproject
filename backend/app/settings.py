"""Process configuration, read from environment variables only (AGENTS.md §7)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from app import messages
from app.constants import (
    DEFAULT_LLM_DAILY_CLASSIFICATION_LIMIT,
    DEFAULT_LLM_DAILY_REGISTRATION_LIMIT,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    DEFAULT_MESSAGE_MAX_ATTEMPTS,
    DEFAULT_MESSAGE_RETRY_FIRST_WAIT_SECONDS,
    DEFAULT_MESSAGE_RETRY_MAX_WAIT_SECONDS,
    DEFAULT_QUEUE_MAX_WAIT_MINUTES,
    DEFAULT_VERSION,
    DEFAULT_WORKER_LOCK_SECONDS,
    DISABLED,
    ENABLED,
    LIST_SEPARATOR,
    Environment,
    EnvVar,
)


class SettingsError(Exception):
    """The environment is incomplete or invalid. The message never carries a value."""


@dataclass(frozen=True)
class Settings:
    # Out of the repr: it carries the password of the database.
    database_url: str = field(repr=False)
    environment: Environment
    version: str
    # Folder with the compiled dashboard, or None when this process does not serve it.
    dashboard_dir: Path | None = None
    # The development entry, which opens a session without a login code (ADR 0016).
    dev_entry_enabled: bool = False
    # The chat of the dashboard, for development and demonstration (ADR 0002, ADR 0016).
    web_chat_enabled: bool = False
    # How long a pending message may wait before GET /queuez fails.
    queue_max_wait_minutes: int = DEFAULT_QUEUE_MAX_WAIT_MINUTES
    # How long a message stays taken by one worker (ADR 0010).
    worker_lock_seconds: int = DEFAULT_WORKER_LOCK_SECONDS
    # The longest a call to the model may take; shorter than the lock (ADR 0010).
    llm_timeout_seconds: int = DEFAULT_LLM_TIMEOUT_SECONDS
    # The retries of a message whose call to the model failed (ADR 0010, point 4).
    message_max_attempts: int = DEFAULT_MESSAGE_MAX_ATTEMPTS
    message_retry_first_wait_seconds: int = DEFAULT_MESSAGE_RETRY_FIRST_WAIT_SECONDS
    message_retry_max_wait_seconds: int = DEFAULT_MESSAGE_RETRY_MAX_WAIT_SECONDS
    # The daily limits of use of each user (domain rules, § 12).
    llm_daily_classification_limit: int = DEFAULT_LLM_DAILY_CLASSIFICATION_LIMIT
    llm_daily_registration_limit: int = DEFAULT_LLM_DAILY_REGISTRATION_LIMIT
    # Only the worker calls the model, so only the worker requires it. Never logged.
    openai_api_key: str | None = field(default=None, repr=False)


def _read(environ: Mapping[str, str], name: EnvVar, default: str = "") -> str:
    return environ.get(name, default).strip()


def _read_switch(environ: Mapping[str, str], name: EnvVar) -> bool:
    """Off unless it says so: a deployment that forgot the variable stays closed."""
    value = _read(environ, name)
    if value not in ("", ENABLED, DISABLED):
        allowed = LIST_SEPARATOR.join((ENABLED, DISABLED))
        raise SettingsError(messages.INVALID_ENV_VAR.format(name=name, allowed=allowed))
    return value == ENABLED


def _read_positive_integer(environ: Mapping[str, str], name: EnvVar, default: int) -> int:
    """A whole number greater than zero, or the default when the variable is not set."""
    value = _read(environ, name)
    if not value:
        return default
    # Only ASCII digits: no sign, no decimals, and no digits of other scripts.
    if not (value.isascii() and value.isdigit()) or int(value) == 0:
        raise SettingsError(messages.NOT_A_POSITIVE_INTEGER.format(name=name))
    return int(value)


def _read_scaffold_switch(
    environ: Mapping[str, str], name: EnvVar, environment: Environment
) -> bool:
    """A part of the scaffold: with it on, no process starts in production (ADR 0016)."""
    enabled = _read_switch(environ, name)
    if enabled and environment is Environment.PRODUCTION:
        raise SettingsError(
            messages.NOT_ALLOWED_IN_ENVIRONMENT.format(name=name, environment=environment)
        )
    return enabled


def load_settings(environ: Mapping[str, str]) -> Settings:
    database_url = _read(environ, EnvVar.DATABASE_URL)
    if not database_url:
        raise SettingsError(messages.MISSING_ENV_VAR.format(name=EnvVar.DATABASE_URL))
    # No default: a deployment that forgot it must not end up running as local.
    declared_environment = _read(environ, EnvVar.APP_ENV)
    if not declared_environment:
        raise SettingsError(messages.MISSING_ENV_VAR.format(name=EnvVar.APP_ENV))
    try:
        environment = Environment(declared_environment)
    except ValueError:
        allowed = LIST_SEPARATOR.join(Environment)
        raise SettingsError(
            messages.INVALID_ENV_VAR.format(name=EnvVar.APP_ENV, allowed=allowed)
        ) from None
    dev_entry_enabled = _read_scaffold_switch(environ, EnvVar.DEV_ENTRY_ENABLED, environment)
    web_chat_enabled = _read_scaffold_switch(environ, EnvVar.WEB_CHAT_ENABLED, environment)
    dashboard_dir = _read(environ, EnvVar.DASHBOARD_DIR)
    worker_lock_seconds = _read_positive_integer(
        environ, EnvVar.WORKER_LOCK_SECONDS, DEFAULT_WORKER_LOCK_SECONDS
    )
    llm_timeout_seconds = _read_positive_integer(
        environ, EnvVar.LLM_TIMEOUT_SECONDS, DEFAULT_LLM_TIMEOUT_SECONDS
    )
    # Every process checks it, so that a worker that would be displaced never starts.
    if worker_lock_seconds <= llm_timeout_seconds:
        raise SettingsError(
            messages.LOCK_NOT_LONGER_THAN_CALL.format(
                lock=EnvVar.WORKER_LOCK_SECONDS, call=EnvVar.LLM_TIMEOUT_SECONDS
            )
        )
    return Settings(
        database_url=database_url,
        environment=environment,
        version=_read(environ, EnvVar.APP_VERSION) or DEFAULT_VERSION,
        dashboard_dir=Path(dashboard_dir) if dashboard_dir else None,
        dev_entry_enabled=dev_entry_enabled,
        web_chat_enabled=web_chat_enabled,
        queue_max_wait_minutes=_read_positive_integer(
            environ, EnvVar.QUEUE_MAX_WAIT_MINUTES, DEFAULT_QUEUE_MAX_WAIT_MINUTES
        ),
        worker_lock_seconds=worker_lock_seconds,
        llm_timeout_seconds=llm_timeout_seconds,
        message_max_attempts=_read_positive_integer(
            environ, EnvVar.MESSAGE_MAX_ATTEMPTS, DEFAULT_MESSAGE_MAX_ATTEMPTS
        ),
        message_retry_first_wait_seconds=_read_positive_integer(
            environ,
            EnvVar.MESSAGE_RETRY_FIRST_WAIT_SECONDS,
            DEFAULT_MESSAGE_RETRY_FIRST_WAIT_SECONDS,
        ),
        message_retry_max_wait_seconds=_read_positive_integer(
            environ, EnvVar.MESSAGE_RETRY_MAX_WAIT_SECONDS, DEFAULT_MESSAGE_RETRY_MAX_WAIT_SECONDS
        ),
        llm_daily_classification_limit=_read_positive_integer(
            environ, EnvVar.LLM_DAILY_CLASSIFICATION_LIMIT, DEFAULT_LLM_DAILY_CLASSIFICATION_LIMIT
        ),
        llm_daily_registration_limit=_read_positive_integer(
            environ, EnvVar.LLM_DAILY_REGISTRATION_LIMIT, DEFAULT_LLM_DAILY_REGISTRATION_LIMIT
        ),
        openai_api_key=_read(environ, EnvVar.OPENAI_API_KEY) or None,
    )


def require_openai_api_key(settings: Settings) -> str:
    """The key of the model, for the process that calls it: without it, it does not start."""
    if settings.openai_api_key is None:
        raise SettingsError(messages.MISSING_ENV_VAR.format(name=EnvVar.OPENAI_API_KEY))
    return settings.openai_api_key
