"""A JSON answer whose amounts keep their exact digits.

A `Decimal` is written as a JSON number with its own digits, `0.30` and not `0.3` or a
string, so an amount never goes through a float on its way out (docs/convenciones-de-
desarrollo.md, section 2).
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

from fastapi.responses import JSONResponse

JsonValue = (
    Decimal | uuid.UUID | str | int | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)


class ExactJSONResponse(JSONResponse):
    def render(self, content: JsonValue) -> bytes:
        return _encode(content).encode()


def _encode(value: JsonValue) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, uuid.UUID):
        return json.dumps(str(value))
    if isinstance(value, dict):
        members = (f"{json.dumps(key)}:{_encode(item)}" for key, item in value.items())
        return "{" + ",".join(members) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    return json.dumps(value)
