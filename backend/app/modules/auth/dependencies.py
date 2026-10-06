"""Auth wiring for FastAPI: builds the service per request, and the
`CurrentUser` dependency every other module uses to protect its routes:

    @router.get("/thing")
    async def thing(user: CurrentUser) -> ...
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import Settings
from app.core.errors import Unauthorized
from app.db.dependencies import get_app_settings, get_session
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService, AuthSettings, ClientInfo

_bearer = HTTPBearer(auto_error=False)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AuthService:
    return AuthService(
        AuthRepository(session),
        AuthSettings(
            jwt_secret=settings.jwt_secret.get_secret_value(),
            access_token_ttl_seconds=settings.access_token_ttl_seconds,
            refresh_token_ttl_days=settings.refresh_token_ttl_days,
        ),
    )


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> uuid.UUID:
    """Verify `Authorization: Bearer <access token>`; 401 otherwise. No DB hit."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthorized("Missing access token", code="TOKEN_MISSING")
    user_id = security.decode_access_token(
        credentials.credentials, secret=settings.jwt_secret.get_secret_value()
    )
    if user_id is None:
        raise Unauthorized("Invalid or expired access token", code="TOKEN_INVALID")
    return user_id


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]


def client_info(request: Request) -> ClientInfo:
    user_agent = request.headers.get("user-agent")
    return ClientInfo(
        user_agent=user_agent[:256] if user_agent else None,
        ip=request.client.host if request.client else None,
    )
