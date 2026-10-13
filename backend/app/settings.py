"""Process configuration, read from environment variables only (AGENTS.md §7)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app import messages
from app.constants import (
    DEFAULT_VERSION,
    LIST_SEPARATOR,
    Environment,
    EnvVar,
)


class SettingsError(Exception):
    """The environment is incomplete or invalid. The message never carries a value."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    environment: Environment
    version: str
    # Folder with the compiled dashboard, or None when this process does not serve it.
    dashboard_dir: Path | None = None


def _read(environ: Mapping[str, str], name: EnvVar, default: str = "") -> str:
    return environ.get(name, default).strip()


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
    dashboard_dir = _read(environ, EnvVar.DASHBOARD_DIR)
    return Settings(
        database_url=database_url,
        environment=environment,
        version=_read(environ, EnvVar.APP_VERSION) or DEFAULT_VERSION,
        dashboard_dir=Path(dashboard_dir) if dashboard_dir else None,
    )
