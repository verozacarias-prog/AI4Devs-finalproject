"""Exchange rates, indicators and the two tables of model usage: cases 102 to 110, and 132."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from tests.integration.schema.names import (
    EUROS,
    OUTSIDE_THE_SET,
)
from tests.integration.schema.rows import OPENED_AT, Rows

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("rate", [Decimal("0"), Decimal("-1200")])
def test_an_exchange_rate_is_positive(rows: Rows, rate: Decimal) -> None:
    # Case 102.
    rows.exchange_rate()

    with rows.rejected_by("ck_exchange_rate_rate"):
        rows.exchange_rate(rate=rate, rate_at=OPENED_AT + timedelta(hours=1))


def test_a_source_publishes_one_rate_per_pair_and_moment(rows: Rows) -> None:
    # Case 103. Another source, another pair or a later moment is another rate.
    rows.exchange_rate()
    rows.exchange_rate(source="DOLAR_OFICIAL")
    rows.exchange_rate(base_currency=EUROS)
    rows.exchange_rate(rate_at=OPENED_AT + timedelta(hours=1))

    with rows.rejected_by("uq_exchange_rate_source_pair_rate_at"):
        rows.exchange_rate(rate=Decimal("1250"))


def test_a_source_publishes_one_indicator_value_per_date(rows: Rows) -> None:
    # Case 104.
    rows.indicator_value()
    rows.indicator_value(source="BCRA_TIME_DEPOSIT_30D")

    with rows.rejected_by("uq_indicator_value_source_date"):
        rows.indicator_value(value=Decimal("3.1"))


def test_the_quota_of_a_usage_row_comes_from_a_closed_set_that_includes_classification(
    rows: Rows,
) -> None:
    # Case 106.
    user = rows.user()
    rows.llm_usage(user, quota="classification")

    with rows.rejected_by("ck_llm_usage_quota"):
        rows.llm_usage(user, quota="embedding")


def test_the_message_count_of_a_usage_row_is_not_negative(rows: Rows) -> None:
    # Case 132.
    user = rows.user()
    rows.llm_usage(user, message_count=0)

    with rows.rejected_by("ck_llm_usage_message_count"):
        rows.llm_usage(user, quota="query", message_count=-1)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("purpose", OUTSIDE_THE_SET),
        ("outcome", OUTSIDE_THE_SET),
        ("duration_ms", -1),
        ("estimated_cost_usd", Decimal("-0.000001")),
    ],
    ids=["107", "108", "109", "110"],
)
def test_a_model_call_uses_the_closed_sets_and_has_no_negative_duration_or_cost(
    rows: Rows, column: str, value: object
) -> None:
    # Cases 107 to 110.
    rows.llm_call(purpose="embedding", outcome="blocked", duration_ms=0, estimated_cost_usd=0)

    with rows.rejected_by(f"ck_llm_call_{column}"):
        rows.llm_call(**{column: value})
