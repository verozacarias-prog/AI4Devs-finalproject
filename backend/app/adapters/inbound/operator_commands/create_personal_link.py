"""Creates the personal link of a person who will try the demo environment.

Run it in the shell of the environment, with
`python -m app.adapters.inbound.operator_commands.create_personal_link <label>`.
It refuses to run in production (ADR 0016).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from typing import TextIO

from app import messages
from app.adapters.inbound.operator_commands.runner import run_command
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.constants import DASHBOARD_PREFIX, EXIT_FAILED, LINE_END
from app.domain.use_cases.test_data.personal_links import CreatePersonalLink
from app.settings import Settings


def _run(label: str, settings: Settings) -> str:
    engine = create_db_engine(settings.database_url)
    try:
        value = CreatePersonalLink(
            SqlAlchemyUnitOfWork(engine),
            settings.environment,
            settings.server_secret_key,
        ).execute(label)
    finally:
        engine.dispose()
    return messages.PERSONAL_LINK_READY.format(path=f"{DASHBOARD_PREFIX}/#{value}")


def main(
    arguments: Sequence[str],
    environ: Mapping[str, str],
    out: TextIO,
    log_stream: TextIO | None = None,
) -> int:
    if len(arguments) != 1 or not arguments[0].strip():
        out.write(messages.PERSONAL_LINK_USAGE + LINE_END)
        return EXIT_FAILED
    command: Callable[[Settings], str] = partial(_run, arguments[0].strip())
    return run_command(command, environ, out, log_stream)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ, sys.stdout))
