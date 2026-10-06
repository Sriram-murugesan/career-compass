"""Auth request/response schemas (camelCase on the wire, matching the frontend contract)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.core.schema import ApiModel


class SignUpRequest(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    # 8-128: long enough to resist guessing, capped so hashing cost stays bounded.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name is required")
        return value.strip()

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.lower()


class SignInRequest(ApiModel):
    email: EmailStr
    # No length rules on sign-in: never reveal which passwords are "possible".
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.lower()


class AuthUser(ApiModel):
    id: uuid.UUID
    name: str
    email: str
    is_onboarded: bool


class AuthSession(ApiModel):
    token: str
    expires_at: datetime
    user: AuthUser


class CurrentUserResponse(ApiModel):
    user: AuthUser


class SignedOut(ApiModel):
    signed_out: bool = True
