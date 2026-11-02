"""Cases 21 and 38 of issue #84: what the versioned Render configuration says (ADR 0029)."""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
BLUEPRINT = REPOSITORY / "render.yaml"

ENV_VAR = re.compile(r"^\s*- key:\s*(\S+)\s*\n\s*(\w+):\s*(.*)$", re.MULTILINE)
SECRETS = {
    "APPLICATION_DB_PASSWORD",
    "DATABASE_URL",
    "MIGRATIONS_DATABASE_URL",
    "OPENAI_API_KEY",
    "SERVER_SECRET_KEY",
}


def _env_vars() -> list[tuple[str, str, str]]:
    return ENV_VAR.findall(BLUEPRINT.read_text())


def test_the_blueprint_declares_the_demo_environment_without_the_value_of_any_secret() -> None:
    env_vars = _env_vars()

    environments = [value for name, _, value in env_vars if name == "APP_ENV"]
    assert environments, "the blueprint does not declare APP_ENV"
    assert set(environments) == {"demo"}

    secrets = [(name, kind, value) for name, kind, value in env_vars if name in SECRETS]
    assert {name for name, _, _ in secrets} == SECRETS
    for name, kind, value in secrets:
        assert (kind, value) == ("sync", "false"), f"{name} must be loaded in Render"


# What only the migration needs: the connection of the owner of the tables (ADR 0030).
OWNER_ONLY = {"APPLICATION_DB_PASSWORD", "MIGRATIONS_DATABASE_URL"}
SERVICE = re.compile(r"^  - type: (\w+)\n(.*?)(?=^  - type: |^\S)", re.MULTILINE | re.DOTALL)
START = re.compile(r"^\s*dockerCommand:\s*(.+)$", re.MULTILINE)


def test_only_the_migration_receives_the_connection_of_the_owner() -> None:
    """Case 38: the worker never gets it, and the web service starts without it."""
    services = dict(SERVICE.findall(BLUEPRINT.read_text()))

    worker_variables = {name for name, _, _ in ENV_VAR.findall(services["worker"])}
    assert not worker_variables & OWNER_ONLY

    start = START.search(services["web"])
    assert start is not None, "the web service does not say how it starts"
    command = start.group(1)
    for name in OWNER_ONLY:
        assert f"-u {name}" in command, f"the web service starts with {name}"
    assert command.endswith("python -m app.adapters.inbound.api.main")
