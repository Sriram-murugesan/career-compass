"""HTTP LAYER for chat and the agent orchestration stream (Server-Sent Events)."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app import endpoints as ep
from app.core.responses import Envelope, ok
from app.modules.auth import CurrentUserId
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.schemas import (
    AgentOut,
    ConversationDetail,
    ConversationOut,
    CreateConversation,
    OrchestrateRequest,
)
from app.modules.chat.service import ChatService

router = APIRouter(tags=["chat"])

Service = Annotated[ChatService, Depends(get_chat_service)]


@router.get(ep.AGENTS, response_model=Envelope[list[AgentOut]])
async def list_agents(_: CurrentUserId, service: Service) -> Envelope[list[AgentOut]]:
    return ok(service.list_agents())


@router.get(ep.CHAT_CONVERSATIONS, response_model=Envelope[list[ConversationOut]])
async def list_conversations(
    user_id: CurrentUserId, service: Service
) -> Envelope[list[ConversationOut]]:
    return ok(await service.list_conversations(user_id))


@router.post(ep.CHAT_CONVERSATIONS, status_code=201, response_model=Envelope[ConversationOut])
async def create_conversation(
    body: CreateConversation, user_id: CurrentUserId, service: Service
) -> Envelope[ConversationOut]:
    return ok(await service.create_conversation(user_id, body.title))


@router.get(ep.CHAT_CONVERSATION, response_model=Envelope[ConversationDetail])
async def get_conversation(
    conversation_id: uuid.UUID, user_id: CurrentUserId, service: Service
) -> Envelope[ConversationDetail]:
    return ok(await service.get_conversation(user_id, conversation_id))


@router.post(ep.CHAT_ORCHESTRATE)
async def orchestrate(
    body: OrchestrateRequest, user_id: CurrentUserId, service: Service
) -> StreamingResponse:
    """Run the agents for one message and stream progress as text/event-stream:

    event: step
    data: {"type":"step","agentId":"resume","status":"running",...}
    """
    conversation_id, profile, history = await service.prepare_turn(
        user_id, body.conversation_id, body.message
    )

    async def events() -> AsyncIterator[str]:
        async for event in service.stream_turn(
            user_id, conversation_id, body.message, profile, history
        ):
            yield _sse(event)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: dict[str, Any]) -> str:
    return f"event: {event.get('type', 'message')}\ndata: {json.dumps(event, default=str)}\n\n"
