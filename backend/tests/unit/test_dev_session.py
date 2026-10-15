"""The session the development entry opens, and how long it is valid (ADR 0016).

Cases 28 to 32, 35, 36, 38 to 43, 53 and 54, on the use cases alone: the clock is fixed, so the
limits of a session are checked to the minute.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.constants import Environment
from app.domain.entities.user import User
from app.domain.errors import NotFoundError, UnauthenticatedError
from app.domain.use_cases.sessions.authenticate_session import AuthenticateSession
from app.domain.use_cases.sessions.close_session import CloseSession
from app.domain.use_cases.sessions.open_dev_session import OpenDevSession, OpenedSession
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from tests.support.doubles import FixedClock, InMemoryUnitOfWork

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


def _on_october_12(hour: int, minute: int = 0) -> datetime:
    """An instant of October 12, written as the hour in Buenos Aires."""
    return datetime(2026, 10, 12, hour, minute, tzinfo=BUENOS_AIRES).astimezone(UTC)


TEN = _on_october_12(10)


def _user(unit_of_work: InMemoryUnitOfWork, name: str, phone: str) -> User:
    return CreateTestUser(FixedClock(TEN)).execute(
        unit_of_work, name=name, phone=phone, terms_version="local-seed-1"
    )


@pytest.fixture
def unit_of_work() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def lucia(unit_of_work: InMemoryUnitOfWork) -> User:
    return _user(unit_of_work, "Lucía", "+000000000001")


def _open(
    unit_of_work: InMemoryUnitOfWork,
    user: User,
    at: datetime = TEN,
    environment: Environment = Environment.LOCAL,
) -> OpenedSession:
    return OpenDevSession(unit_of_work, FixedClock(at), environment).execute(user_id=user.id)


def _authenticate(unit_of_work: InMemoryUnitOfWork, token: str | None, at: datetime) -> User:
    return AuthenticateSession(unit_of_work, FixedClock(at)).execute(token)


def test_a_session_opened_at_ten_expires_at_ten_at_night(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 28.
    opened = _open(unit_of_work, lucia)

    [session] = unit_of_work.sessions.stored.values()
    assert session == opened.session
    assert session.user_id == lucia.id
    assert session.created_at == TEN
    assert session.last_seen_at == TEN
    assert session.expires_at == _on_october_12(22)
    assert session.revoked_at is None
    assert unit_of_work.commits == 1


def test_the_store_keeps_the_hash_of_the_token_and_never_the_token(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 29.
    opened = _open(unit_of_work, lucia)

    [session] = unit_of_work.sessions.stored.values()
    assert opened.token
    assert session.token_hash
    assert opened.token not in session.token_hash
    assert opened.token not in repr(session)


def test_entering_twice_opens_two_sessions_and_the_first_one_still_works(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 30.
    first = _open(unit_of_work, lucia)
    second = _open(unit_of_work, lucia)

    assert first.token != second.token
    assert len(unit_of_work.sessions.stored) == 2
    assert _authenticate(unit_of_work, first.token, TEN) == lucia
    assert _authenticate(unit_of_work, second.token, TEN) == lucia


def test_a_user_who_does_not_exist_is_not_found_and_gets_no_session(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 31.
    use_case = OpenDevSession(unit_of_work, FixedClock(TEN), Environment.LOCAL)

    with pytest.raises(NotFoundError) as error:
        use_case.execute(user_id=uuid.uuid4())

    assert error.value.code == "not_found"
    assert unit_of_work.sessions.stored == {}


def test_a_user_with_a_real_phone_is_not_found_either(unit_of_work: InMemoryUnitOfWork) -> None:
    # Case 32.
    real = _user(unit_of_work, "Vero", "+5491100000000")

    with pytest.raises(NotFoundError) as error:
        _open(unit_of_work, real)

    assert error.value.code == "not_found"
    assert unit_of_work.sessions.stored == {}


@pytest.mark.parametrize("access_token", [None, "a-personal-link"], ids=["alone", "with-link"])
def test_outside_local_nobody_enters_by_choosing_a_user(
    unit_of_work: InMemoryUnitOfWork, lucia: User, access_token: str | None
) -> None:
    # Case 35.
    use_case = OpenDevSession(unit_of_work, FixedClock(TEN), Environment.DEMO)

    with pytest.raises(NotFoundError) as error:
        use_case.execute(user_id=lucia.id, access_token=access_token)

    assert error.value.code == "not_found"
    assert unit_of_work.sessions.stored == {}


@pytest.mark.parametrize("environment", [Environment.LOCAL, Environment.DEMO])
def test_a_personal_link_is_unknown_until_links_exist(
    unit_of_work: InMemoryUnitOfWork, lucia: User, environment: Environment
) -> None:
    # Case 36.
    use_case = OpenDevSession(unit_of_work, FixedClock(TEN), environment)

    with pytest.raises(NotFoundError) as error:
        use_case.execute(access_token="a-personal-link")

    assert error.value.code == "not_found"
    assert unit_of_work.sessions.stored == {}


@pytest.mark.parametrize(
    "token", [None, "", "not-a-token-of-anybody"], ids=["38", "38-empty", "39"]
)
def test_without_a_token_of_a_session_nobody_is_authenticated(
    unit_of_work: InMemoryUnitOfWork, lucia: User, token: str | None
) -> None:
    # Cases 38 and 39.
    _open(unit_of_work, lucia)

    with pytest.raises(UnauthenticatedError) as error:
        _authenticate(unit_of_work, token, TEN)

    assert error.value.code == "unauthorized"


def test_a_revoked_session_no_longer_authenticates(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 40.
    opened = _open(unit_of_work, lucia)
    unit_of_work.sessions.revoke(opened.session.id, _on_october_12(10, 5))

    with pytest.raises(UnauthenticatedError):
        _authenticate(unit_of_work, opened.token, _on_october_12(10, 6))


def test_twelve_hours_after_it_was_opened_a_session_is_over_even_if_it_was_just_used(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 41. Opened at 10:00 and used at 21:59: at 22:00 it is over.
    opened = _open(unit_of_work, lucia)
    unit_of_work.sessions.touch(opened.session.id, _on_october_12(21, 59))

    with pytest.raises(UnauthenticatedError):
        _authenticate(unit_of_work, opened.token, _on_october_12(22))


def test_thirty_minutes_without_activity_end_a_session(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 42. Last used at 10:00: at 10:30 it is over.
    opened = _open(unit_of_work, lucia)

    with pytest.raises(UnauthenticatedError):
        _authenticate(unit_of_work, opened.token, _on_october_12(10, 30))

    assert unit_of_work.sessions.stored[opened.session.id].last_seen_at == TEN


def test_a_session_used_within_thirty_minutes_goes_on_and_counts_the_activity(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 43. Last used at 10:00: at 10:29 it still works, and 10:29 is its last activity.
    opened = _open(unit_of_work, lucia)
    commits = unit_of_work.commits

    user = _authenticate(unit_of_work, opened.token, _on_october_12(10, 29))

    assert user == lucia
    assert unit_of_work.sessions.stored[opened.session.id] == replace(
        opened.session, last_seen_at=_on_october_12(10, 29)
    )
    assert unit_of_work.commits == commits + 1


def test_closing_a_session_revokes_it(unit_of_work: InMemoryUnitOfWork, lucia: User) -> None:
    # Case 53.
    opened = _open(unit_of_work, lucia)
    other = _open(unit_of_work, lucia)

    CloseSession(unit_of_work, FixedClock(_on_october_12(10, 10))).execute(opened.token)

    assert unit_of_work.sessions.stored[opened.session.id].revoked_at == _on_october_12(10, 10)
    with pytest.raises(UnauthenticatedError):
        _authenticate(unit_of_work, opened.token, _on_october_12(10, 11))
    # Only the session of the request is closed.
    assert _authenticate(unit_of_work, other.token, _on_october_12(10, 11)) == lucia


def test_there_is_nothing_to_close_without_a_valid_session(
    unit_of_work: InMemoryUnitOfWork, lucia: User
) -> None:
    # Case 54.
    opened = _open(unit_of_work, lucia)
    close_at_eleven = CloseSession(unit_of_work, FixedClock(_on_october_12(11)))

    with pytest.raises(UnauthenticatedError) as error:
        close_at_eleven.execute(None)
    assert error.value.code == "unauthorized"
    # Idle since 10:00, so at 11:00 it is no longer a session to close.
    with pytest.raises(UnauthenticatedError):
        close_at_eleven.execute(opened.token)
    assert unit_of_work.sessions.stored[opened.session.id].revoked_at is None
