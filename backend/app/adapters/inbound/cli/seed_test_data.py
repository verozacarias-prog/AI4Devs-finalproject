"""Creates the test users of the local environment.

Run it with `python -m app.adapters.inbound.cli.seed_test_data`.

It refuses to run in any other environment, and running it again changes nothing
(docs/operacion.md, section 2).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import TextIO

from app import messages
from app.adapters.outbound.clock.system_clock import SystemClock
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.constants import EXIT_OK, EXIT_REFUSED, LINE_END, Environment
from app.domain.use_cases.create_test_user import CreateTestUser
from app.domain.use_cases.seed_test_data import SeedTestData, TestDataNotAllowedError
from app.settings import load_settings


def main(environ: Mapping[str, str], out: TextIO) -> int:
    settings = load_settings(environ)
    engine = create_db_engine(settings.database_url)
    clock = SystemClock()
    seed = SeedTestData(
        SqlAlchemyUnitOfWork(engine), clock, CreateTestUser(clock), settings.environment
    )
    try:
        report = seed.execute()
    except TestDataNotAllowedError as error:
        out.write(
            messages.TEST_DATA_NOT_ALLOWED.format(
                allowed=Environment.LOCAL, current=error.environment
            )
            + LINE_END
        )
        return EXIT_REFUSED
    finally:
        engine.dispose()
    out.write(
        messages.TEST_DATA_SEEDED.format(created=report.created, existing=report.existing)
        + LINE_END
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(os.environ, sys.stdout))
