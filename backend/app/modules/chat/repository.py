"""DATA LAYER for conversations and messages."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.modules.chat.models import ChatMessage, Conversation


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_conversation(self, user_id: uuid.UUID, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def get_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_conversations(self, user_id: uuid.UUID, limit: int = 50) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            conversation_id=conversation.id, role=role, content=content, payload=payload
        )
        conversation.updated_at = utcnow()
        self.session.add(message)
        await self.session.flush()
        return message

    async def messages(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[ChatMessage]:
        """Oldest → newest. With a limit: the most recent `limit` messages."""
        query = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
        if limit is None:
            result = await self.session.execute(query.order_by(ChatMessage.created_at))
            return list(result.scalars().all())
        result = await self.session.execute(
            query.order_by(ChatMessage.created_at.desc()).limit(limit)
        )
        return list(reversed(result.scalars().all()))
