from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from zoneinfo import ZoneInfo

from app.constants import CHAT_FIRST_READ_MESSAGES
from app.domain.entities.chat_message import ChatMessage
from app.domain.errors import ErrorCode, NotFoundError, UnauthenticatedError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort


@dataclass(frozen=True)
class ChatPage:
    messages: list[ChatMessage]
    # Where the next read starts: the last message, or the same cursor when nothing is new.
    next_cursor: uuid.UUID | None


class ListChatMessages:
    """The conversation of the web chat, with each time in the time zone of the user."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, user_id: uuid.UUID, after: uuid.UUID | None = None) -> ChatPage:
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            if user is None:
                raise UnauthenticatedError
            if after is not None and not unit_of_work.chat_messages.contains(user_id, after):
                # A cursor of someone else's conversation, or of none: told apart nowhere.
                raise NotFoundError(ErrorCode.NOT_FOUND)
            # Only the first read has a limit: one from a cursor would skip messages.
            latest = CHAT_FIRST_READ_MESSAGES if after is None else None
            messages = unit_of_work.chat_messages.list_by_user(user_id, after, latest)
        zone = ZoneInfo(user.time_zone)
        local = [
            replace(message, created_at=message.created_at.astimezone(zone)) for message in messages
        ]
        return ChatPage(messages=local, next_cursor=local[-1].id if local else after)
