"""A JSON answer whose amounts keep their exact digits.

A `Decimal` is written as a JSON number with its own digits, `0.30` and not `0.3` or a
string, so an amount never goes through a float on its way out (docs/convenciones-de-
desarrollo.md, section 2).
"""

from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi.responses import JSONResponse
from pydantic import WithJsonSchema

# An amount travels as a JSON number with its exact digits, never as a string.
ExactAmount = Annotated[Decimal, WithJsonSchema({"type": "number"})]

# An amount a client sends: a JSON number or a decimal text, kept exact (docs/04-api.md).
AmountInput = Annotated[
    Decimal, WithJsonSchema({"anyOf": [{"type": "number"}, {"type": "string"}]})
]

JsonValue = (
    Decimal
    | uuid.UUID
    | date
    | str
    | int
    | bool
    | None
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)


class ExactJSONResponse(JSONResponse):
    def render(self, content: JsonValue) -> bytes:
        return _encode(content).encode()


def _encode(value: JsonValue) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, uuid.UUID):
        return json.dumps(str(value))
    if isinstance(value, date):
        return json.dumps(value.isoformat())
    if isinstance(value, dict):
        members = (f"{json.dumps(key)}:{_encode(item)}" for key, item in value.items())
        return "{" + ",".join(members) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    return json.dumps(value)
