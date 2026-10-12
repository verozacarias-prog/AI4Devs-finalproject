"""Process configuration, read from environment variables only (AGENTS.md §7)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app import messages
from app.constants import DEFAULT_ENVIRONMENT, DEFAULT_VERSION, Environment, EnvVar


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
    try:
        environment = Environment(_read(environ, EnvVar.APP_ENV, DEFAULT_ENVIRONMENT))
    except ValueError:
        allowed = ", ".join(Environment)
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
