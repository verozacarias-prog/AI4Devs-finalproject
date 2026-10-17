"""Each process says at start that the scaffold is on (FEAT-002, its spec.md; ADR 0016).

Cases C3-07 to C3-09: with the web chat or the development entry on, the API and the worker
leave a `dev.scaffold_enabled` line when they start, so nobody leaves them on without knowing.
"""

from __future__ import annotations

import io

import pytest

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.message_worker.worker import create_worker
from app.settings import Settings, load_settings
from tests.support.chat_data import NOW
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.log_lines import events_of

pytestmark = pytest.mark.integration


def _settings(database_url: str, **switches: str) -> Settings:
    return load_settings(
        {"DATABASE_URL": database_url, "APP_ENV": "local", "APP_VERSION": "test", **switches}
    )


def test_with_the_chat_on_the_api_says_so_when_it_starts(database_url: str) -> None:
    # Case C3-07.
    stream = io.StringIO()

    create_app(_settings(database_url, WEB_CHAT_ENABLED="true"), log_stream=stream)

    [line] = events_of(stream, "dev.scaffold_enabled")
    assert line["level"] == "WARNING"


@pytest.mark.parametrize("switch", ["WEB_CHAT_ENABLED", "DEV_ENTRY_ENABLED"])
def test_with_the_chat_or_the_entry_on_the_worker_says_so_when_it_starts(
    database_url: str, switch: str
) -> None:
    # Case C3-08.
    stream = io.StringIO()

    create_worker(
        _settings(database_url, **{switch: "true"}),
        FixedClock(NOW),
        log_stream=stream,
        llm=FakeLLM(),
    )

    [line] = events_of(stream, "dev.scaffold_enabled")
    assert line["level"] == "WARNING"
    assert line["process"] == "worker"


def test_with_both_off_no_process_says_anything(database_url: str) -> None:
    # Case C3-09.
    api_stream = io.StringIO()
    worker_stream = io.StringIO()
    settings = _settings(database_url)

    create_app(settings, log_stream=api_stream)
    create_worker(settings, FixedClock(NOW), log_stream=worker_stream, llm=FakeLLM())

    assert events_of(api_stream, "dev.scaffold_enabled") == []
    assert events_of(worker_stream, "dev.scaffold_enabled") == []
