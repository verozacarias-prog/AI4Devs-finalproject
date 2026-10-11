"""Shared test fixtures.

Integration tests need a real PostgreSQL with pgvector (ADR 0021). The URL comes from
TEST_DATABASE_URL; by default it points at the database started by `docker compose up db`.
"""
from __future__ import annotations

import os

import pytest

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://platita:platita@127.0.0.1:5433/platita"
# A port nobody listens on: the "database is down" of cases 2 and 4.
UNREACHABLE_DATABASE_URL = "postgresql+psycopg://platita:platita@127.0.0.1:9/platita"


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
