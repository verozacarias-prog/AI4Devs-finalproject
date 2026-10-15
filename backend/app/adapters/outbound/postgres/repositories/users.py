from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.user import OnboardingStatus, User


class PostgresUserRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, user: User) -> None:
        execute_write(self._connection, queries.INSERT_USER, asdict(user))

    def find_by_phone(self, phone: str) -> User | None:
        row = self._connection.execute(
            text(queries.SELECT_USER_BY_PHONE), {"phone": phone}
        ).one_or_none()
        return None if row is None else _user_from(row)

    def find_by_id(self, user_id: uuid.UUID) -> User | None:
        row = self._connection.execute(
            text(queries.SELECT_USER_BY_ID), {"user_id": user_id}
        ).one_or_none()
        return None if row is None else _user_from(row)

    def list_by_phone_prefix(self, prefix: str) -> list[User]:
        rows = self._connection.execute(
            text(queries.SELECT_USERS_BY_PHONE_PREFIX), {"prefix": prefix}
        ).all()
        return [_user_from(row) for row in rows]


def _user_from(row: Row[tuple[object, ...]]) -> User:
    return User(
        id=row.id,
        name=row.name,
        whatsapp_phone=row.whatsapp_phone,
        country=row.country,
        time_zone=row.time_zone,
        primary_currency=row.primary_currency,
        exchange_rate_reference=row.exchange_rate_reference,
        terms_accepted_at=row.terms_accepted_at,
        terms_version=row.terms_version,
        notifications_opt_in=row.notifications_opt_in,
        onboarding_status=OnboardingStatus(row.onboarding_status),
    )
