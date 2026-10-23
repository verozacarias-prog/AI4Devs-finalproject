"""Reading the JSON log lines a test captured in a stream."""

from __future__ import annotations

import io
import json

LogLine = dict[str, str | int | float | bool | list[str] | None]


def lines_of(stream: io.StringIO) -> list[LogLine]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def events_of(stream: io.StringIO, event: str) -> list[LogLine]:
    return [line for line in lines_of(stream) if line["event"] == event]


def stack_of(line: LogLine) -> list[str]:
    stack = line["error_stack"]
    assert isinstance(stack, list)
    return stack
