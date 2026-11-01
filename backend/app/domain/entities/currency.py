from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    """A currency of the catalog, which the migrations load and every user shares."""

    code: str
    name: str
