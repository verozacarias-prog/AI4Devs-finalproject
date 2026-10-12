"""TRANSFER, RECURRING_RULE and CARD_STATEMENT: cases 63 to 84, and block D."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from tests.integration.schema.names import (
    AUTOMATIC,
    DOLLARS,
    INCOME,
    MONTHLY,
    OUTSIDE_THE_SET,
    PESOS_PER_DOLLAR,
)
from tests.integration.schema.rows import Rows

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class Wallets:
    user: uuid.UUID
    pesos: uuid.UUID
    savings: uuid.UUID
    dollars: uuid.UUID


@pytest.fixture
def wallets(rows: Rows) -> Wallets:
    user = rows.user()
    return Wallets(
        user=user,
        pesos=rows.account(user),
        savings=rows.account(user),
        dollars=rows.account(user, currency=DOLLARS),
    )


def _to_dollars(**overrides: object) -> dict[str, object]:
    """1,200,000 pesos that become 1,000 dollars."""
    return {
        "from_amount": Decimal("1200000.00"),
        "to_amount": Decimal("1000.00"),
        "to_currency": DOLLARS,
        "exchange_rate": PESOS_PER_DOLLAR,
        **overrides,
    }


@pytest.mark.parametrize("late", ["origin", "destination"])
def test_a_transfer_is_not_dated_before_either_account_was_opened(
    rows: Rows, wallets: Wallets, late: str
) -> None:
    # Case 63.
    opened_in_february = rows.account(wallets.user, created_at=datetime(2026, 2, 1, 12, tzinfo=UTC))
    origin, destination = (
        (opened_in_february, wallets.pesos)
        if late == "origin"
        else (wallets.pesos, opened_in_february)
    )
    rows.transfer(wallets.user, origin, destination, transfer_date=date(2026, 2, 1))

    with rows.rejected_by("tg_transfer_before_account"):
        rows.transfer(wallets.user, origin, destination, transfer_date=date(2026, 1, 31))


def test_the_origin_of_a_transfer_belongs_to_its_user(rows: Rows, wallets: Wallets) -> None:
    # Case 64.
    rows.transfer(wallets.user, wallets.pesos, wallets.savings)
    foreign = rows.account(rows.user())

    with rows.rejected_by("fk_transfer_from_account"):
        rows.transfer(wallets.user, foreign, wallets.savings)


def test_the_destination_of_a_transfer_belongs_to_its_user(rows: Rows, wallets: Wallets) -> None:
    # Case 65.
    rows.transfer(wallets.user, wallets.pesos, wallets.savings)
    foreign = rows.account(rows.user())

    with rows.rejected_by("fk_transfer_to_account"):
        rows.transfer(wallets.user, wallets.pesos, foreign)


def test_a_repeated_dashboard_request_does_not_create_a_second_transfer(
    rows: Rows, wallets: Wallets
) -> None:
    # Case 66.
    key = uuid.uuid4()
    rows.transfer(wallets.user, wallets.pesos, wallets.savings, client_request_id=key)

    with rows.rejected_by("uq_transfer_user_client_request"):
        rows.transfer(wallets.user, wallets.pesos, wallets.savings, client_request_id=key)


def test_a_transfer_goes_between_two_different_accounts(rows: Rows, wallets: Wallets) -> None:
    # Case 126.
    rows.transfer(wallets.user, wallets.pesos, wallets.savings)

    with rows.rejected_by("ck_transfer_distinct_accounts"):
        rows.transfer(wallets.user, wallets.pesos, wallets.pesos)


@pytest.mark.parametrize("side", ["from", "to"])
@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("-1.00")])
def test_both_amounts_of_a_transfer_are_positive(
    rows: Rows, wallets: Wallets, side: str, amount: Decimal
) -> None:
    # Case 127. Between two currencies, so the amounts are free to differ.
    rows.transfer(wallets.user, wallets.pesos, wallets.dollars, **_to_dollars())

    with rows.rejected_by(f"ck_transfer_{side}_amount"):
        rows.transfer(
            wallets.user,
            wallets.pesos,
            wallets.dollars,
            **_to_dollars(**{f"{side}_amount": amount}),
        )


def test_the_amounts_and_the_rate_of_a_transfer_follow_its_currencies(
    rows: Rows, wallets: Wallets
) -> None:
    # Case 128.
    rows.transfer(wallets.user, wallets.pesos, wallets.savings)
    rows.transfer(wallets.user, wallets.pesos, wallets.dollars, **_to_dollars())

    with rows.rejected_by("ck_transfer_currencies"):
        rows.transfer(wallets.user, wallets.pesos, wallets.savings, to_amount=Decimal("999.00"))
    with rows.rejected_by("ck_transfer_currencies"):
        rows.transfer(wallets.user, wallets.pesos, wallets.savings, exchange_rate=Decimal("1"))
    with rows.rejected_by("ck_transfer_currencies"):
        rows.transfer(
            wallets.user, wallets.pesos, wallets.dollars, **_to_dollars(exchange_rate=None)
        )


def test_the_source_of_a_transfer_comes_from_a_closed_set(rows: Rows, wallets: Wallets) -> None:
    # Case 133.
    rows.transfer(wallets.user, wallets.pesos, wallets.savings, source=AUTOMATIC)

    with rows.rejected_by("ck_transfer_source"):
        rows.transfer(wallets.user, wallets.pesos, wallets.savings, source=OUTSIDE_THE_SET)


def test_a_rule_charges_the_budget_of_a_user_or_of_a_group_never_of_none(rows: Rows) -> None:
    # Case 67.
    home = rows.home()
    rows.rule(home)
    rows.rule(home, budget_user_id=None, budget_family_group_id=rows.group())

    with rows.rejected_by("ck_recurring_rule_one_budget_owner"):
        rows.rule(home, budget_user_id=None)


def test_a_rule_does_not_charge_the_budget_of_a_user_and_of_a_group_at_once(rows: Rows) -> None:
    # Case 68.
    home = rows.home()
    rows.rule(home)

    with rows.rejected_by("ck_recurring_rule_one_budget_owner"):
        rows.rule(home, budget_family_group_id=rows.group())


@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("-9000.00")])
def test_the_amount_of_a_rule_is_positive(rows: Rows, amount: Decimal) -> None:
    # Case 69.
    home = rows.home()
    rows.rule(home)

    with rows.rejected_by("ck_recurring_rule_amount"):
        rows.rule(home, amount=amount)


def test_a_rule_is_in_the_currency_of_its_account(rows: Rows) -> None:
    # Case 70.
    home = rows.home()
    rows.rule(home)

    with rows.rejected_by("fk_recurring_rule_account"):
        rows.rule(home, currency=DOLLARS)


def test_a_rule_does_not_use_the_account_of_another_user(rows: Rows) -> None:
    # Case 71.
    home = rows.home()
    rows.rule(home)
    foreign = rows.account(rows.user())

    with rows.rejected_by("fk_recurring_rule_account"):
        rows.rule(home, account_id=foreign)


def test_a_broker_account_takes_no_rules(rows: Rows) -> None:
    # Case 72.
    home = rows.home()
    rows.rule(home)
    broker = rows.account(home.user, type="broker")

    with rows.rejected_by("tg_recurring_rule_broker_account"):
        rows.rule(home, account_id=broker)


def test_the_individual_budget_of_a_rule_is_the_one_of_its_own_user(rows: Rows) -> None:
    # Case 73.
    home = rows.home()
    rows.rule(home)

    with rows.rejected_by("ck_recurring_rule_budget_user"):
        rows.rule(home, budget_user_id=rows.user())


def test_a_rule_does_not_generate_more_occurrences_than_it_has(rows: Rows) -> None:
    # Case 74. "Installment 5 of 12" starts with 4 already generated.
    home = rows.home()
    rows.rule(home, occurrences=12, generated_occurrences=4)
    rows.rule(home, occurrences=12, generated_occurrences=12)

    with rows.rejected_by("ck_recurring_rule_generated_occurrences"):
        rows.rule(home, occurrences=12, generated_occurrences=13)


@pytest.mark.parametrize(
    ("frequency", "valid_day", "invalid_day"),
    [
        ("weekly", 7, 8),
        ("weekly", 1, 0),
        (MONTHLY, 31, 32),
        (MONTHLY, 1, 0),
        ("yearly", None, 10),
    ],
    ids=["75 above", "75 below", "76 above", "76 below", "77"],
)
def test_the_execution_day_of_a_rule_depends_on_its_frequency(
    rows: Rows, frequency: str, valid_day: int | None, invalid_day: int
) -> None:
    # Cases 75, 76 and 77.
    home = rows.home()
    rows.rule(home, frequency=frequency, execution_day=valid_day)

    with rows.rejected_by("ck_recurring_rule_execution_day"):
        rows.rule(home, frequency=frequency, execution_day=invalid_day)


def test_a_rule_with_an_end_has_a_fixed_amount(rows: Rows) -> None:
    # Case 78.
    home = rows.home()
    rows.rule(home, amount_varies=True, amount_confirmed_until=date(2026, 6, 30))

    with rows.rejected_by("ck_recurring_rule_varies_without_end"):
        rows.rule(home, amount_varies=True, occurrences=6)


def test_only_a_rule_of_variable_amount_says_until_when_its_amount_is_confirmed(
    rows: Rows,
) -> None:
    # Case 79.
    home = rows.home()
    rows.rule(home, amount_varies=True, amount_confirmed_until=date(2026, 6, 30))

    with rows.rejected_by("ck_recurring_rule_confirmed_until"):
        rows.rule(home, amount_confirmed_until=date(2026, 6, 30))


def test_the_category_of_a_rule_is_of_its_same_type(rows: Rows) -> None:
    # Case 80.
    home = rows.home()
    income = rows.category(home.user, kind=INCOME)
    rows.rule(home, type=INCOME, category_id=income)

    with rows.rejected_by("fk_recurring_rule_category_kind"):
        rows.rule(home, category_id=income)


def test_a_rule_with_an_end_has_at_least_one_occurrence(rows: Rows) -> None:
    # Case 129.
    home = rows.home()
    rows.rule(home, occurrences=1)

    with rows.rejected_by("ck_recurring_rule_occurrences"):
        rows.rule(home, occurrences=0)


def test_the_frequency_of_a_rule_comes_from_a_closed_set(rows: Rows) -> None:
    # Case 129.
    home = rows.home()
    rows.rule(home)

    with rows.rejected_by("ck_recurring_rule_frequency"):
        rows.rule(home, frequency="daily")


def test_a_card_has_one_statement_per_closing_date(rows: Rows) -> None:
    # Case 81. Another card may close the same day.
    user = rows.user()
    card = rows.card(user)
    rows.card_statement(card)
    rows.card_statement(rows.card(user))

    with rows.rejected_by("uq_card_statement_account_closing"):
        rows.card_statement(card, due_date=date(2026, 4, 6))


def test_a_card_has_one_statement_per_due_date(rows: Rows) -> None:
    # Case 82.
    card = rows.card(rows.user())
    rows.card_statement(card)

    with rows.rejected_by("uq_card_statement_account_due"):
        rows.card_statement(card, closing_date=date(2026, 3, 21))


def test_a_statement_is_due_after_it_closes(rows: Rows) -> None:
    # Case 83.
    card = rows.card(rows.user())
    rows.card_statement(card)

    with rows.rejected_by("ck_card_statement_due_after_closing"):
        rows.card_statement(card, closing_date=date(2026, 5, 20), due_date=date(2026, 5, 20))


@pytest.mark.parametrize("rate", [Decimal("0"), Decimal("-1200")])
def test_the_exchange_rate_of_a_statement_is_positive(rows: Rows, rate: Decimal) -> None:
    # Case 84.
    card = rows.card(rows.user())
    rows.card_statement(card, exchange_rate=PESOS_PER_DOLLAR)

    with rows.rejected_by("ck_card_statement_exchange_rate"):
        rows.card_statement(
            card, closing_date=date(2026, 4, 20), due_date=date(2026, 5, 5), exchange_rate=rate
        )


def test_the_status_of_a_statement_comes_from_a_closed_set(rows: Rows) -> None:
    # Case 133.
    card = rows.card(rows.user())
    rows.card_statement(card, status="reconciled")

    with rows.rejected_by("ck_card_statement_status"):
        rows.card_statement(
            card, closing_date=date(2026, 4, 20), due_date=date(2026, 5, 5), status=OUTSIDE_THE_SET
        )
