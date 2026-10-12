"""Users, groups, invitations and the tables of the login: cases 6 to 21, and block D."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal

import pytest

from tests.integration.schema.names import (
    OUTSIDE_THE_CATALOG,
    OUTSIDE_THE_SET,
    OWNER,
)
from tests.integration.schema.rows import OPENED_AT, Rows

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("missing", ["name", "country", "time_zone", "primary_currency"])
def test_a_completed_onboarding_needs_name_country_time_zone_and_currency(
    rows: Rows, missing: str
) -> None:
    # Case 6.
    rows.user()

    with rows.rejected_by("ck_app_user_onboarding_completed"):
        rows.user(**{missing: None})


def _user_currency(rows: Rows) -> None:
    rows.user(primary_currency=OUTSIDE_THE_CATALOG)


def _period_currency(rows: Rows) -> None:
    rows.period(user=rows.user(), primary_currency=OUTSIDE_THE_CATALOG)


def _account_currency(rows: Rows) -> None:
    rows.account(rows.user(), currency=OUTSIDE_THE_CATALOG)


def _transaction_currency(rows: Rows) -> None:
    rows.transaction(rows.home(), currency=OUTSIDE_THE_CATALOG, exchange_rate=Decimal("1"))


def _rate_base_currency(rows: Rows) -> None:
    rows.exchange_rate(base_currency=OUTSIDE_THE_CATALOG)


def _rate_quote_currency(rows: Rows) -> None:
    rows.exchange_rate(quote_currency=OUTSIDE_THE_CATALOG)


def _transfer_from_currency(rows: Rows) -> None:
    user = rows.user()
    rows.transfer(
        user,
        rows.account(user),
        rows.account(user),
        from_currency=OUTSIDE_THE_CATALOG,
        exchange_rate=Decimal("1"),
    )


def _transfer_to_currency(rows: Rows) -> None:
    user = rows.user()
    rows.transfer(
        user,
        rows.account(user),
        rows.account(user),
        to_currency=OUTSIDE_THE_CATALOG,
        exchange_rate=Decimal("1"),
    )


def _rule_currency(rows: Rows) -> None:
    rows.rule(rows.home(), currency=OUTSIDE_THE_CATALOG)


# A transfer and a recurring rule also tie their currency to the one of the account, so either
# foreign key may be the one that answers.
CURRENCY_COLUMNS: list[tuple[tuple[str, ...], Callable[[Rows], None]]] = [
    (("fk_app_user_primary_currency",), _user_currency),
    (("fk_budget_period_primary_currency",), _period_currency),
    (("fk_account_currency",), _account_currency),
    (("fk_transaction_currency",), _transaction_currency),
    (("fk_exchange_rate_base_currency",), _rate_base_currency),
    (("fk_exchange_rate_quote_currency",), _rate_quote_currency),
    (("fk_transfer_from_currency", "fk_transfer_from_account"), _transfer_from_currency),
    (("fk_transfer_to_currency", "fk_transfer_to_account"), _transfer_to_currency),
    (("fk_recurring_rule_currency", "fk_recurring_rule_account"), _rule_currency),
]


@pytest.mark.parametrize(
    ("constraints", "insert"), CURRENCY_COLUMNS, ids=[names[0] for names, _ in CURRENCY_COLUMNS]
)
def test_a_currency_code_outside_the_catalog_is_rejected_in_every_currency_column(
    rows: Rows, constraints: tuple[str, ...], insert: Callable[[Rows], None]
) -> None:
    # Case 7.
    with rows.rejected_by(*constraints):
        insert(rows)


def test_a_phone_belongs_to_one_user(rows: Rows) -> None:
    # Case 142.
    rows.user(whatsapp_phone="+5491100000001")

    with rows.rejected_by("uq_app_user_whatsapp_phone"):
        rows.user(whatsapp_phone="+5491100000001")


def test_a_user_keeps_a_phone_unless_the_account_is_deleted(rows: Rows) -> None:
    # Case 116.
    rows.user()
    rows.user(account_status="deleted", whatsapp_phone=None, deactivated_at=OPENED_AT)

    with rows.rejected_by("ck_app_user_phone_iff_deleted"):
        rows.user(whatsapp_phone=None)
    with rows.rejected_by("ck_app_user_phone_iff_deleted"):
        rows.user(account_status="deleted", deactivated_at=OPENED_AT)


def test_a_deactivated_or_deleted_account_needs_deactivated_at(rows: Rows) -> None:
    # Case 117.
    rows.user(account_status="deactivated", deactivated_at=OPENED_AT)

    with rows.rejected_by("ck_app_user_deactivated_at"):
        rows.user(account_status="deactivated")
    with rows.rejected_by("ck_app_user_deactivated_at"):
        rows.user(account_status="deleted", whatsapp_phone=None)


@pytest.mark.parametrize("column", ["onboarding_status", "account_status"])
def test_the_statuses_of_a_user_come_from_a_closed_set(rows: Rows, column: str) -> None:
    # Case 118.
    rows.user()

    with rows.rejected_by(f"ck_app_user_{column}"):
        rows.user(**{column: OUTSIDE_THE_SET})


def test_a_membership_role_is_owner_or_member(rows: Rows) -> None:
    # Case 8.
    group = rows.group()
    rows.membership(rows.user(), group, role=OWNER)

    with rows.rejected_by("ck_user_group_role"):
        rows.membership(rows.user(), group, role="admin")


def test_a_group_has_one_current_owner(rows: Rows) -> None:
    # Case 9. An owner who left does not count.
    group = rows.group()
    rows.membership(rows.user(), group, role=OWNER, left_at=OPENED_AT + timedelta(days=1))
    rows.membership(rows.user(), group, role=OWNER)

    with rows.rejected_by("uq_user_group_current_owner"):
        rows.membership(rows.user(), group, role=OWNER)


def test_a_member_cannot_leave_before_joining(rows: Rows) -> None:
    # Case 10.
    group = rows.group()
    rows.membership(rows.user(), group, left_at=OPENED_AT + timedelta(days=1))

    with rows.rejected_by("ck_user_group_left_after_joined"):
        rows.membership(rows.user(), group, left_at=OPENED_AT - timedelta(days=1))


def test_a_user_has_one_membership_per_group(rows: Rows) -> None:
    # Case 11.
    group, user = rows.group(), rows.user()
    rows.membership(user, group)

    with rows.rejected_by("pk_user_group"):
        rows.membership(user, group)


def test_an_invitation_code_hash_is_unique(rows: Rows) -> None:
    # Case 12.
    group, owner = rows.group(), rows.user()
    rows.invitation(group, owner, code_hash="same-hash")

    with rows.rejected_by("uq_group_invitation_code_hash"):
        rows.invitation(group, owner, code_hash="same-hash")


def test_an_invitation_is_used_by_someone_at_some_time_or_not_at_all(rows: Rows) -> None:
    # Case 13.
    group, owner, guest = rows.group(), rows.user(), rows.user()
    rows.invitation(group, owner, used_by=guest, used_at=OPENED_AT + timedelta(days=1))

    with rows.rejected_by("ck_group_invitation_used_together"):
        rows.invitation(group, owner, used_by=guest)
    with rows.rejected_by("ck_group_invitation_used_together"):
        rows.invitation(group, owner, used_at=OPENED_AT + timedelta(days=1))


def test_a_used_invitation_cannot_be_revoked(rows: Rows) -> None:
    # Case 14.
    group, owner, guest = rows.group(), rows.user(), rows.user()
    later = OPENED_AT + timedelta(days=1)
    rows.invitation(group, owner, revoked_at=later)

    with rows.rejected_by("ck_group_invitation_used_not_revoked"):
        rows.invitation(group, owner, used_by=guest, used_at=later, revoked_at=later)


def test_an_invitation_expires_after_it_was_created(rows: Rows) -> None:
    # Case 15.
    group, owner = rows.group(), rows.user()
    rows.invitation(group, owner)

    with rows.rejected_by("ck_group_invitation_expires_after_created"):
        rows.invitation(group, owner, expires_at=OPENED_AT)


def test_a_login_code_allows_five_attempts(rows: Rows) -> None:
    # Case 16.
    user = rows.user()
    rows.login_code(user, attempts=5)

    with rows.rejected_by("ck_login_code_attempts"):
        rows.login_code(user, attempts=6)


def test_a_login_code_has_a_known_purpose(rows: Rows) -> None:
    # Case 133.
    user = rows.user()
    rows.login_code(user, purpose="account_deletion")

    with rows.rejected_by("ck_login_code_purpose"):
        rows.login_code(user, purpose="password_reset")


@pytest.mark.parametrize("column", ["event", "key_type"], ids=["17", "133"])
def test_an_auth_throttle_row_uses_the_closed_sets(rows: Rows, column: str) -> None:
    # Cases 17 and 133.
    rows.auth_throttle(key_type="ip", event="not_enabled_notice")

    with rows.rejected_by(f"ck_auth_throttle_{column}"):
        rows.auth_throttle(**{column: OUTSIDE_THE_SET})


def test_a_test_user_has_one_personal_link(rows: Rows) -> None:
    # Case 18. Links nobody opened yet have no user and do not collide.
    user = rows.user()
    rows.dev_access_link()
    rows.dev_access_link()
    rows.dev_access_link(user_id=user)

    with rows.rejected_by("uq_dev_access_link_user_id"):
        rows.dev_access_link(user_id=user)


@pytest.mark.parametrize("column", ["token_hash", "label"], ids=["19", "20"])
def test_a_personal_link_does_not_repeat_its_token_hash_or_its_label(
    rows: Rows, column: str
) -> None:
    # Cases 19 and 20.
    rows.dev_access_link(**{column: "same"})

    with rows.rejected_by(f"uq_dev_access_link_{column}"):
        rows.dev_access_link(**{column: "same"})


def test_a_phone_is_enabled_once(rows: Rows) -> None:
    # Case 21.
    rows.allowed_phone(phone_hash="same-hash")

    with rows.rejected_by("uq_allowed_phone_phone_hash"):
        rows.allowed_phone(phone_hash="same-hash")


def test_a_phone_is_disabled_after_it_was_enabled(rows: Rows) -> None:
    # Case 122.
    rows.allowed_phone(disabled_at=OPENED_AT + timedelta(days=1))

    with rows.rejected_by("ck_allowed_phone_disabled_after_enabled"):
        rows.allowed_phone(disabled_at=OPENED_AT)


def test_a_session_token_hash_is_unique(rows: Rows) -> None:
    # Case 120.
    user = rows.user()
    rows.session(user, token_hash="same-hash")

    with rows.rejected_by("uq_session_token_hash"):
        rows.session(user, token_hash="same-hash")


def test_a_session_expires_after_it_was_created(rows: Rows) -> None:
    # Case 121.
    user = rows.user()
    rows.session(user)

    with rows.rejected_by("ck_session_expires_after_created"):
        rows.session(user, expires_at=OPENED_AT)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("dependents", -1),
        ("emergency_fund_months", Decimal("-0.5")),
        ("income_range", OUTSIDE_THE_SET),
        ("main_goal", OUTSIDE_THE_SET),
    ],
)
def test_a_financial_profile_rejects_negative_numbers_and_unknown_options(
    rows: Rows, column: str, value: object
) -> None:
    # Case 131. Every answer is optional, so an empty profile is valid.
    rows.financial_profile(rows.user())
    rows.financial_profile(
        rows.user(), dependents=0, emergency_fund_months=Decimal("0"), main_goal="save"
    )

    with rows.rejected_by(f"ck_financial_profile_{column}"):
        rows.financial_profile(rows.user(), **{column: value})
