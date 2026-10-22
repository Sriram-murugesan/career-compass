"""BUSINESS LAYER for chat: one turn = save the question, run the agents,
stream their progress, save the answer.

Streaming outlives a normal request transaction, so the service opens short
units of work (`self.uow()`) around each database step instead of holding one
session open while the agents run.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any

from app.core.errors import NotFound
from app.modules.chat.repository import ChatRepository
from app.modules.chat.schemas import (
    AgentOut,
    ConversationDetail,
    ConversationOut,
    MessageOut,
)
from app.modules.profile import ProfileService
from app.orchestrator import Orchestrator

logger = logging.getLogger("app.chat")

HISTORY_MESSAGES = 10


@dataclass
class ChatUnitOfWork:
    chat: ChatRepository
    profile: ProfileService


UnitOfWorkFactory = Callable[[], AbstractAsyncContextManager[ChatUnitOfWork]]


class ChatService:
    def __init__(self, uow: UnitOfWorkFactory, orchestrator: Orchestrator) -> None:
        self.uow = uow
        self.orchestrator = orchestrator

    def list_agents(self) -> list[AgentOut]:
        return [
            AgentOut(id=a.id, name=a.name, description=a.description, reads=list(a.reads))
            for a in self.orchestrator.agents
        ]

    async def list_conversations(self, user_id: uuid.UUID) -> list[ConversationOut]:
        async with self.uow() as uow:
            rows = await uow.chat.list_conversations(user_id)
            return [ConversationOut.model_validate(row) for row in rows]

    async def create_conversation(self, user_id: uuid.UUID, title: str) -> ConversationOut:
        async with self.uow() as uow:
            return ConversationOut.model_validate(
                await uow.chat.create_conversation(user_id, title)
            )

    async def get_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> ConversationDetail:
        async with self.uow() as uow:
            conversation = await uow.chat.get_conversation(user_id, conversation_id)
            if conversation is None:
                raise NotFound("Conversation not found")
            messages = await uow.chat.messages(conversation.id)
            return ConversationDetail(
                id=conversation.id,
                title=conversation.title,
                updated_at=conversation.updated_at,
                messages=[MessageOut.model_validate(m) for m in messages],
            )

    async def delete_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        async with self.uow() as uow:
            if not await uow.chat.delete_conversation(user_id, conversation_id):
                raise NotFound("Conversation not found")

    async def prepare_turn(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID | None, message: str
    ) -> tuple[uuid.UUID, dict[str, Any], list[dict[str, str]]]:
        """Save the user's message. Returns (conversation id, profile snapshot, history).

        Runs before streaming starts, so a bad conversation id is a normal 404.
        """
        async with self.uow() as uow:
            if conversation_id is None:
                conversation = await uow.chat.create_conversation(user_id, _title_from(message))
            else:
                found = await uow.chat.get_conversation(user_id, conversation_id)
                if found is None:
                    raise NotFound("Conversation not found")
                conversation = found
            history = [
                {"role": m.role, "content": m.content}
                for m in await uow.chat.messages(conversation.id, limit=HISTORY_MESSAGES)
            ]
            await uow.chat.add_message(conversation, "user", message)
            profile = await uow.profile.snapshot(user_id)
            return conversation.id, profile, history

    async def stream_turn(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message: str,
        profile: dict[str, Any],
        history: list[dict[str, str]],
        agents: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "conversation", "conversationId": str(conversation_id)}
        answer: dict[str, Any] | None = None
        try:
            async for event in self.orchestrator.stream(
                user_id=user_id,
                conversation_id=conversation_id,
                request=message,
                profile=profile,
                history=history,
                agents=agents,
            ):
                if event.get("type") == "answer":
                    answer = event
                yield event
        except Exception:
            logger.exception("orchestration failed")
            yield {"type": "error", "message": "The agents hit a problem. Please try again."}
            return

        if answer is not None:
            async with self.uow() as uow:
                conversation = await uow.chat.get_conversation(user_id, conversation_id)
                if conversation is not None:
                    await uow.chat.add_message(
                        conversation,
                        "assistant",
                        str(answer["answer"]),
                        payload={"steps": answer["steps"], "agentOutputs": answer["agentOutputs"]},
                    )
        yield {"type": "done"}


def _title_from(message: str) -> str:
    title = " ".join(message.split())
    return title if len(title) <= 60 else title[:57] + "…"
