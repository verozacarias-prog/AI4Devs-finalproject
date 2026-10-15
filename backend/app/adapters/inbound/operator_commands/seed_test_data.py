"""Creates the test users of the local environment.

Run it with `python -m app.adapters.inbound.operator_commands.seed_test_data`.

It refuses to run in any other environment, and running it again changes nothing
(docs/operacion.md, section 2).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import TextIO

from app import messages
from app.adapters.inbound.operator_commands.runner import run_command
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from app.domain.use_cases.test_data.seed_test_data import SeedTestData
from app.settings import Settings
from app.shared.clock import SystemClock


def seed(settings: Settings) -> str:
    engine = create_db_engine(settings.database_url)
    clock = SystemClock()
    try:
        report = SeedTestData(
            SqlAlchemyUnitOfWork(engine), clock, CreateTestUser(clock), settings.environment
        ).execute()
    finally:
        engine.dispose()
    return messages.TEST_DATA_SEEDED.format(created=report.created, existing=report.existing)


def main(environ: Mapping[str, str], out: TextIO, log_stream: TextIO | None = None) -> int:
    return run_command(seed, environ, out, log_stream)


if __name__ == "__main__":
    sys.exit(main(os.environ, sys.stdout))
