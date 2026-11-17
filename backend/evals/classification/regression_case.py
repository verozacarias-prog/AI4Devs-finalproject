"""One message of the regression set, and what the model has to answer to it."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.entities.classification import ClassificationRequest
from app.domain.services.transactions.movement_resolution import Interpretation


@dataclass(frozen=True)
class RegressionCase:
    """A request to the model and the fields its answer is checked on.

    The keys of `expected` are paths of the classification: "account", "more_movements.0.amount"
    or "more_movements.length". A field the case does not name is not compared.
    """

    name: str
    request: ClassificationRequest
    expected: Mapping[str, object]
    # In a reply to a pending, what was understood of it: the code checks the reply against it.
    previous: Interpretation | None = None
