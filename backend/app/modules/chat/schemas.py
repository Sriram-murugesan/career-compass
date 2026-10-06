from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.schema import ApiModel


class OrchestrateRequest(ApiModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None  # omit to start a new conversation


class CreateConversation(ApiModel):
    title: str = Field(default="New conversation", min_length=1, max_length=120)


class ConversationOut(ApiModel):
    id: uuid.UUID
    title: str
    updated_at: datetime


class MessageOut(ApiModel):
    id: uuid.UUID
    role: str
    content: str
    payload: dict[str, Any] | None
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class AgentOut(ApiModel):
    id: str
    name: str
    description: str
    reads: list[str]
