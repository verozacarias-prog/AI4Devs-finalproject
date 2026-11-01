"""Case 21 of issue #84: what the versioned Render configuration says (ADR 0029)."""

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
