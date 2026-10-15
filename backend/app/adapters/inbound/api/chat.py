"""The web chat of the dashboard (docs/04-api.md, ADR 0010).

This router is installed only when the web chat is enabled, so turned off its routes do not
exist. Writing goes the same way as a message of WhatsApp: it is stored, and the worker
answers it later.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Header, Query, status
from pydantic import BaseModel, Field

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.errors import documented_errors
from app.adapters.inbound.api.routes import CHAT_MESSAGES, CHAT_TAG, IDEMPOTENCY_KEY_HEADER
from app.adapters.inbound.api.session import SessionToken
from app.domain.entities.chat_message import Direction
from app.domain.entities.inbound_message import InboundStatus
from app.domain.entities.outbound_message import ResponseKind
from app.domain.use_cases.authenticate_session import AuthenticateSession, ValidateSession
from app.domain.use_cases.list_chat_messages import ListChatMessages
from app.domain.use_cases.send_chat_message import SendChatMessage


class ChatMessageRequest(BaseModel):
    text: str = Field(min_length=1, description=reference.CHAT_TEXT)
    quoted_message_id: uuid.UUID | None = Field(
        default=None, description=reference.CHAT_QUOTED_MESSAGE_ID
    )


class StoredChatMessage(BaseModel):
    id: uuid.UUID = Field(description=reference.CHAT_MESSAGE_ID)
    status: InboundStatus = Field(description=reference.CHAT_MESSAGE_STATUS)


class ChatMessageItem(BaseModel):
    id: uuid.UUID = Field(description=reference.CHAT_MESSAGE_ID)
    direction: Direction = Field(description=reference.CHAT_DIRECTION)
    text: str = Field(description=reference.CHAT_TEXT)
    quoted_message_id: uuid.UUID | None = Field(description=reference.CHAT_QUOTED_MESSAGE_ID)
    response_kind: ResponseKind | None = Field(description=reference.CHAT_RESPONSE_KIND)
    created_at: datetime = Field(description=reference.CHAT_CREATED_AT)


class ChatConversation(BaseModel):
    messages: list[ChatMessageItem] = Field(description=reference.CHAT_MESSAGES)
    next_cursor: uuid.UUID | None = Field(description=reference.CHAT_NEXT_CURSOR)


def build_chat_router(
    authenticate_session: Callable[[], AuthenticateSession],
    validate_session: Callable[[], ValidateSession],
    send_chat_message: Callable[[], SendChatMessage],
    list_chat_messages: Callable[[], ListChatMessages],
) -> APIRouter:
    router = APIRouter(tags=[CHAT_TAG])

    @router.post(
        CHAT_MESSAGES,
        status_code=status.HTTP_202_ACCEPTED,
        summary=reference.SEND_CHAT_MESSAGE_SUMMARY,
        description=reference.SEND_CHAT_MESSAGE_DESCRIPTION,
        response_description=reference.SEND_CHAT_MESSAGE_ACCEPTED,
        responses=documented_errors(
            {
                status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION,
                status.HTTP_403_FORBIDDEN: reference.FOREIGN_REQUEST,
                status.HTTP_422_UNPROCESSABLE_CONTENT: reference.SEND_CHAT_MESSAGE_INVALID,
            }
        ),
    )
    def send(
        body: ChatMessageRequest,
        token: SessionToken,
        idempotency_key: Annotated[
            uuid.UUID, Header(alias=IDEMPOTENCY_KEY_HEADER, description=reference.IDEMPOTENCY_KEY)
        ],
    ) -> StoredChatMessage:
        # Writing counts as activity of the session (ADR 0016).
        user = authenticate_session().execute(token)
        stored = send_chat_message().execute(
            user_id=user.id,
            text=body.text,
            idempotency_key=str(idempotency_key),
            quoted_message_id=body.quoted_message_id,
        )
        return StoredChatMessage(id=stored.id, status=stored.status)

    @router.get(
        CHAT_MESSAGES,
        summary=reference.LIST_CHAT_MESSAGES_SUMMARY,
        description=reference.LIST_CHAT_MESSAGES_DESCRIPTION,
        response_description=reference.LIST_CHAT_MESSAGES_OK,
        responses=documented_errors(
            {
                status.HTTP_401_UNAUTHORIZED: reference.NO_SESSION,
                status.HTTP_422_UNPROCESSABLE_CONTENT: reference.LIST_CHAT_MESSAGES_INVALID,
            }
        ),
    )
    def conversation(
        token: SessionToken,
        after: Annotated[uuid.UUID | None, Query(description=reference.CHAT_AFTER)] = None,
    ) -> ChatConversation:
        # The read the dashboard repeats does not keep the session alive (ADR 0016).
        user = validate_session().execute(token)
        page = list_chat_messages().execute(user.id, after)
        return ChatConversation(
            messages=[
                ChatMessageItem(
                    id=message.id,
                    direction=message.direction,
                    text=message.text,
                    quoted_message_id=message.quoted_message_id,
                    response_kind=message.response_kind,
                    created_at=message.created_at,
                )
                for message in page.messages
            ],
            next_cursor=page.next_cursor,
        )

    return router
