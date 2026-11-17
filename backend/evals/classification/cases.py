"""The messages of the regression set and what the model has to answer to each one.

They come from the approved cases of FEAT-003, FEAT-006 and FEAT-007, where a case says what
the model answers, and from the errors found by hand (issues 134, 178 and 85). They live in
cases.json: a case names only the fields its spec fixes, and a field a spec leaves open is not
there. The messages and the data are made up: the user is Lucía of the tests, with the daily
categories of the base catalog.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.domain.entities.classification import ClassificationRequest, NumberedPending, OpenBatch
from evals.classification import constants
from evals.classification.regression_case import RegressionCase

CASES_FILE = Path(__file__).parent / constants.CASES_FILE_NAME


def _expected_value(path: str, value: object) -> object:
    """A value of cases.json as the classification has it: amounts and dates are not text."""
    if value is None:
        return None
    last = path.rsplit(constants.PATH_SEPARATOR, 1)[-1]
    if last == constants.AMOUNT_FIELD:
        return Decimal(str(value))
    if last == constants.DATE_FIELD:
        return date.fromisoformat(str(value))
    return value


def _batch(data: dict[str, object] | None) -> OpenBatch | None:
    if data is None:
        return None
    pendings = data[constants.PENDINGS_KEY]
    assert isinstance(pendings, list)
    return OpenBatch(
        pendings=tuple(
            NumberedPending(
                number=pending["number"],
                interpreted=pending["interpreted"],
                missing=tuple(pending["missing"]),
            )
            for pending in pendings
        ),
        question=str(data[constants.QUESTION_KEY]),
    )


def _case(data: dict[str, object]) -> RegressionCase:
    today = data.get("today") or constants.DEFAULT_TODAY
    batch = data.get("open_batch")
    expected = data["expected"]
    assert isinstance(expected, dict)
    return RegressionCase(
        name=str(data["name"]),
        request=ClassificationRequest(
            text=str(data["message"]),
            accounts=constants.ACCOUNTS,
            expense_categories=constants.EXPENSE_CATEGORIES,
            income_categories=constants.INCOME_CATEGORIES,
            today=date.fromisoformat(str(today)),
            open_batch=_batch(batch if isinstance(batch, dict) else None),
        ),
        expected={path: _expected_value(path, value) for path, value in expected.items()},
    )


def load_cases(path: Path = CASES_FILE) -> tuple[RegressionCase, ...]:
    return tuple(_case(item) for item in json.loads(path.read_text(encoding="utf-8")))


CASES: tuple[RegressionCase, ...] = load_cases()
