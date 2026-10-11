"""Process configuration, read from environment variables only (AGENTS.md §7)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

ENVIRONMENTS = ("local", "demo", "production")


class SettingsError(Exception):
    """The environment is incomplete or invalid. The message never carries a value."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    environment: str
    version: str


def load_settings(environ: Mapping[str, str]) -> Settings:
    database_url = environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SettingsError("Missing required environment variable: DATABASE_URL")
    environment = environ.get("APP_ENV", "local").strip()
    if environment not in ENVIRONMENTS:
        raise SettingsError(f"APP_ENV must be one of: {', '.join(ENVIRONMENTS)}")
    return Settings(
        database_url=database_url,
        environment=environment,
        version=environ.get("APP_VERSION", "dev").strip() or "dev",
    )
