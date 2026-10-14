"""The balance of each account of a user (FEAT-001, docs/features/FEAT-001/spec.md).

Cases C1-01 to C1-13 and C1-20 to C1-24, the unit ones: the data is built in memory and the
action is to list the accounts of the user, with their balance. Unless a case says otherwise,
the user is from Buenos Aires, their primary currency is ARS, the accounts were opened on
1 October 2026, and today is 15 October 2026.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.entities.account import Account, AccountType, BalanceKind
from app.domain.entities.transaction import Transaction, TransactionType
from app.domain.entities.transfer import Transfer
from app.domain.entities.user import OnboardingStatus, User
from app.domain.use_cases.list_accounts import AccountBalance, ListAccounts
from tests.unit.doubles import FixedClock, InMemoryUnitOfWork

BUENOS_AIRES = "America/Argentina/Buenos_Aires"
PESOS = "ARS"
DOLLARS = "USD"
OPENED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
# Midday in Buenos Aires: 15 October for the user and for the machine alike.
FIFTEENTH_AT_NOON = datetime(2026, 10, 15, 15, 0, tzinfo=UTC)
OCTOBER_5 = date(2026, 10, 5)
OCTOBER_10 = date(2026, 10, 10)
OCTOBER_12 = date(2026, 10, 12)
OCTOBER_15 = date(2026, 10, 15)
OCTOBER_16 = date(2026, 10, 16)
DELETED_AT = datetime(2026, 10, 12, 18, 0, tzinfo=UTC)


def _user(unit_of_work: InMemoryUnitOfWork) -> User:
    user = User(
        id=uuid.uuid4(),
        name="Lucía",
        whatsapp_phone="+000000000001",
        country="AR",
        time_zone=BUENOS_AIRES,
        primary_currency=PESOS,
        exchange_rate_reference=None,
        terms_accepted_at=OPENED_AT,
        terms_version="local-seed-1",
        notifications_opt_in=False,
        onboarding_status=OnboardingStatus.COMPLETED,
    )
    unit_of_work.users.add(user)
    return user


def _account(
    unit_of_work: InMemoryUnitOfWork,
    user: User,
    name: str,
    initial_balance: str,
    *,
    type: AccountType = AccountType.BANK_ACCOUNT,
    currency: str = PESOS,
) -> Account:
    account = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name=name,
        type=type,
        currency=currency,
        initial_balance=Decimal(initial_balance),
        opened_at=OPENED_AT,
    )
    unit_of_work.accounts.add(account)
    return account


def _movement(
    unit_of_work: InMemoryUnitOfWork,
    account: Account,
    type: TransactionType,
    amount: str,
    on: date,
    *,
    currency: str | None = None,
    exchange_rate: str | None = None,
    duplicate_of: uuid.UUID | None = None,
    deleted_at: datetime | None = None,
) -> Transaction:
    transaction = Transaction(
        id=uuid.uuid4(),
        user_id=account.user_id,
        account_id=account.id,
        type=type,
        amount=Decimal(amount),
        currency=currency or account.currency,
        exchange_rate=Decimal(exchange_rate) if exchange_rate is not None else None,
        transaction_date=on,
        duplicate_of=duplicate_of,
        deleted_at=deleted_at,
    )
    unit_of_work.transactions.add(transaction)
    return transaction


def _expense(
    unit_of_work: InMemoryUnitOfWork,
    account: Account,
    amount: str,
    on: date,
    *,
    currency: str | None = None,
    exchange_rate: str | None = None,
    duplicate_of: uuid.UUID | None = None,
    deleted_at: datetime | None = None,
) -> Transaction:
    return _movement(
        unit_of_work,
        account,
        TransactionType.EXPENSE,
        amount,
        on,
        currency=currency,
        exchange_rate=exchange_rate,
        duplicate_of=duplicate_of,
        deleted_at=deleted_at,
    )


def _income(
    unit_of_work: InMemoryUnitOfWork, account: Account, amount: str, on: date
) -> Transaction:
    return _movement(unit_of_work, account, TransactionType.INCOME, amount, on)


def _transfer(
    unit_of_work: InMemoryUnitOfWork,
    source: Account,
    target: Account,
    sent: str,
    on: date,
    *,
    received: str | None = None,
    deleted_at: datetime | None = None,
) -> Transfer:
    same_currency = source.currency == target.currency
    transfer = Transfer(
        id=uuid.uuid4(),
        user_id=source.user_id,
        from_account_id=source.id,
        from_amount=Decimal(sent),
        from_currency=source.currency,
        to_account_id=target.id,
        to_amount=Decimal(received or sent),
        to_currency=target.currency,
        exchange_rate=None if same_currency else Decimal(received or sent) / Decimal(sent),
        transfer_date=on,
        deleted_at=deleted_at,
    )
    unit_of_work.transfers.add(transfer)
    return transfer


def _list(
    unit_of_work: InMemoryUnitOfWork, user: User, now: datetime = FIFTEENTH_AT_NOON
) -> list[AccountBalance]:
    return ListAccounts(unit_of_work, FixedClock(now)).execute(user.id)


def _balance_of(listed: list[AccountBalance], account: Account) -> Decimal:
    return next(item.balance for item in listed if item.account.id == account.id)


def test_an_account_without_movements_keeps_its_initial_balance() -> None:
    # Case C1-01.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("350000.00")


def test_an_expense_subtracts_and_an_income_adds() -> None:
    # Case C1-02: 350.000 − 3.500 + 10.000.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    _expense(unit_of_work, galicia, "3500.00", OCTOBER_15)
    _income(unit_of_work, galicia, "10000.00", OCTOBER_15)

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("356500.00")


def test_a_received_transfer_adds_and_a_sent_one_subtracts() -> None:
    # Case C1-03: 350.000 + 20.000 − 5.000.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    mercado_pago = _account(
        unit_of_work, user, "Mercado Pago", "80000.00", type=AccountType.DIGITAL_WALLET
    )
    cash = _account(unit_of_work, user, "Efectivo", "25000.00", type=AccountType.CASH)
    _transfer(unit_of_work, mercado_pago, galicia, "20000.00", OCTOBER_10)
    _transfer(unit_of_work, galicia, cash, "5000.00", OCTOBER_12)

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("365000.00")


def test_an_expense_dated_tomorrow_does_not_count() -> None:
    # Case C1-04: 350.000 − 3.500; the expense of the 16th does not count.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    _expense(unit_of_work, galicia, "3500.00", OCTOBER_15)
    _expense(unit_of_work, galicia, "9000.00", OCTOBER_16)

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("346500.00")


def test_today_is_the_day_of_the_user_not_of_the_server() -> None:
    # Case C1-05: at 01:00 UTC of the 15th it is still the 14th in Buenos Aires.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    _expense(unit_of_work, galicia, "3500.00", OCTOBER_15)

    listed = _list(unit_of_work, user, now=datetime(2026, 10, 15, 1, 0, tzinfo=UTC))

    assert _balance_of(listed, galicia) == Decimal("350000.00")


def test_the_same_expense_counts_once_its_day_arrives_for_the_user() -> None:
    # Case C1-21: at 03:00 UTC of the 15th it is already the 15th in Buenos Aires.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    _expense(unit_of_work, galicia, "3500.00", OCTOBER_15)

    listed = _list(unit_of_work, user, now=datetime(2026, 10, 15, 3, 0, tzinfo=UTC))

    assert _balance_of(listed, galicia) == Decimal("346500.00")


def test_a_transfer_dated_tomorrow_does_not_count() -> None:
    # Case C1-06.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    mercado_pago = _account(
        unit_of_work, user, "Mercado Pago", "80000.00", type=AccountType.DIGITAL_WALLET
    )
    _transfer(unit_of_work, mercado_pago, galicia, "20000.00", OCTOBER_16)

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("350000.00")


def test_a_deleted_expense_does_not_count() -> None:
    # Case C1-07.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    _expense(unit_of_work, galicia, "3500.00", OCTOBER_10, deleted_at=DELETED_AT)

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("350000.00")


def test_a_duplicated_expense_counts_once() -> None:
    # Case C1-08: 350.000 − 3.500; the duplicate does not count.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    original = _expense(unit_of_work, galicia, "3500.00", OCTOBER_10)
    _expense(unit_of_work, galicia, "3500.00", OCTOBER_10, duplicate_of=original.id)

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("346500.00")


def test_a_deleted_transfer_does_not_count() -> None:
    # Case C1-09.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    cash = _account(unit_of_work, user, "Efectivo", "25000.00", type=AccountType.CASH)
    _transfer(unit_of_work, galicia, cash, "5000.00", OCTOBER_12, deleted_at=DELETED_AT)

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("350000.00")


def test_an_expense_in_dollars_on_an_account_in_pesos_counts_converted() -> None:
    # Case C1-10: 50 × 1.000 = 50.000 pesos, and 350.000 − 50.000.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    _expense(unit_of_work, galicia, "50.00", OCTOBER_10, currency=DOLLARS, exchange_rate="1000")

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("300000.00")


def test_each_movement_is_rounded_before_adding() -> None:
    # Case C1-11: 0,01 × 1.234,5 = 12,345, rounded to 12,35 each; 350.000 − 24,70.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    for _ in range(2):
        _expense(
            unit_of_work, galicia, "0.01", OCTOBER_10, currency=DOLLARS, exchange_rate="1234.5"
        )

    assert _balance_of(_list(unit_of_work, user), galicia) == Decimal("349975.30")


def test_an_investment_account_says_its_number_is_the_net_contributed() -> None:
    # Case C1-12.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    balanz = _account(
        unit_of_work, user, "Balanz USD", "0.00", type=AccountType.BROKER, currency=DOLLARS
    )

    kinds = {item.account.id: item.balance_kind for item in _list(unit_of_work, user)}

    assert kinds == {galicia.id: BalanceKind.BALANCE, balanz.id: BalanceKind.NET_CONTRIBUTED}


def test_the_net_contributed_can_be_negative() -> None:
    # Case C1-13: 0 + 1.000 − 1.200.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia_usd = _account(unit_of_work, user, "Galicia USD", "5000.00", currency=DOLLARS)
    balanz = _account(
        unit_of_work, user, "Balanz USD", "0.00", type=AccountType.BROKER, currency=DOLLARS
    )
    _transfer(unit_of_work, galicia_usd, balanz, "1000.00", OCTOBER_5)
    _transfer(unit_of_work, balanz, galicia_usd, "1200.00", OCTOBER_10)

    assert _balance_of(_list(unit_of_work, user), balanz) == Decimal("-200.00")


def test_what_was_declared_on_opening_counts_as_contributed() -> None:
    # Case C1-20: 3.000 + 1.000.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia_usd = _account(unit_of_work, user, "Galicia USD", "5000.00", currency=DOLLARS)
    balanz = _account(
        unit_of_work, user, "Balanz USD", "3000.00", type=AccountType.BROKER, currency=DOLLARS
    )
    _transfer(unit_of_work, galicia_usd, balanz, "1000.00", OCTOBER_5)

    assert _balance_of(_list(unit_of_work, user), balanz) == Decimal("4000.00")


def test_buying_dollars_between_own_accounts_counts_each_side_in_its_currency() -> None:
    # Case C1-22: 350.000 − 120.000 and 500 + 100, without converting.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    galicia = _account(unit_of_work, user, "Galicia pesos", "350000.00")
    galicia_usd = _account(unit_of_work, user, "Galicia USD", "500.00", currency=DOLLARS)
    _transfer(unit_of_work, galicia, galicia_usd, "120000.00", OCTOBER_10, received="100.00")

    listed = _list(unit_of_work, user)

    assert _balance_of(listed, galicia) == Decimal("230000.00")
    assert _balance_of(listed, galicia_usd) == Decimal("600.00")


def test_a_card_with_unpaid_expenses_already_due_is_negative() -> None:
    # Case C1-24: 0 − 50.000, the same formula as any account.
    unit_of_work = InMemoryUnitOfWork()
    user = _user(unit_of_work)
    visa = _account(unit_of_work, user, "Visa", "0.00", type=AccountType.CREDIT_CARD)
    _expense(unit_of_work, visa, "50000.00", OCTOBER_5)

    assert _balance_of(_list(unit_of_work, user), visa) == Decimal("-50000.00")
