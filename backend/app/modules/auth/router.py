"""HTTP LAYER — translate requests into service calls and results into
responses. No business rules and no SQL here."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app import endpoints as ep
from app.core.config import Settings
from app.core.errors import Unauthorized, Unavailable
from app.core.rate_limit import RateLimiter
from app.core.responses import Envelope, fail_body, ok
from app.db.dependencies import get_app_settings
from app.modules.auth.dependencies import (
    CurrentUserId,
    client_info,
    get_auth_service,
    get_google_verifier,
)
from app.modules.auth.google import GoogleTokenInvalid, GoogleTokenVerifier
from app.modules.auth.schemas import (
    AuthSession,
    CurrentUserResponse,
    GoogleSignInRequest,
    SignedOut,
    SignInRequest,
    SignUpRequest,
)
from app.modules.auth.service import AuthService, IssuedSession, SessionRejected, to_auth_user

logger = logging.getLogger("app.auth")

router = APIRouter(tags=["auth"])

REFRESH_COOKIE = "cc_refresh"
COOKIE_PATH = ep.AUTH_COOKIE_PATH  # the browser sends the refresh token to auth routes only

Service = Annotated[AuthService, Depends(get_auth_service)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]


def _limit(request: Request) -> None:
    """Per-IP limit on credential endpoints (brute force / credential stuffing)."""
    limiter: RateLimiter = request.app.state.auth_rate_limiter
    limiter.check(request.client.host if request.client else "unknown")


RateLimit = Depends(_limit)


def _set_refresh_cookie(response: Response, issued: IssuedSession, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        issued.refresh_token,
        httponly=True,  # unreadable by JavaScript → safe from XSS token theft
        secure=settings.secure_cookies,
        samesite="lax",  # not sent on cross-site POSTs → CSRF-safe for these routes
        path=COOKIE_PATH,
        expires=issued.refresh_expires_at,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        REFRESH_COOKIE, path=COOKIE_PATH, secure=settings.secure_cookies, samesite="lax"
    )


@router.post(
    ep.AUTH_SIGN_UP,
    status_code=status.HTTP_201_CREATED,
    dependencies=[RateLimit],
    response_model=Envelope[AuthSession],
)
async def sign_up(
    body: SignUpRequest,
    request: Request,
    response: Response,
    service: Service,
    settings: AppSettings,
) -> Envelope[AuthSession]:
    issued = await service.sign_up(body, client_info(request))
    logger.info("user signed up", extra={"context": {"userId": str(issued.session.user.id)}})
    _set_refresh_cookie(response, issued, settings)
    return ok(issued.session)


@router.post(ep.AUTH_GOOGLE, dependencies=[RateLimit], response_model=Envelope[AuthSession])
async def sign_in_with_google(
    body: GoogleSignInRequest,
    request: Request,
    response: Response,
    service: Service,
    verifier: Annotated[GoogleTokenVerifier, Depends(get_google_verifier)],
    settings: AppSettings,
) -> Envelope[AuthSession]:
    """Exchange a Google ID token (from the Google button) for our session."""
    if not verifier.enabled:
        raise Unavailable(
            "Google sign-in is not configured on this server", code="GOOGLE_SIGN_IN_DISABLED"
        )
    try:
        identity = await verifier.verify(body.credential)
    except GoogleTokenInvalid as exc:
        logger.info("rejected google credential", extra={"context": {"reason": str(exc)[:120]}})
        raise Unauthorized(
            "Google sign-in failed — please try again", code="GOOGLE_TOKEN_INVALID"
        ) from exc
    issued = await service.sign_in_with_google(identity, client_info(request))
    logger.info(
        "user signed in with google", extra={"context": {"userId": str(issued.session.user.id)}}
    )
    _set_refresh_cookie(response, issued, settings)
    return ok(issued.session)


@router.post(ep.AUTH_SIGN_IN, dependencies=[RateLimit], response_model=Envelope[AuthSession])
async def sign_in(
    body: SignInRequest,
    request: Request,
    response: Response,
    service: Service,
    settings: AppSettings,
) -> Envelope[AuthSession]:
    issued = await service.sign_in(body, client_info(request))
    logger.info("user signed in", extra={"context": {"userId": str(issued.session.user.id)}})
    _set_refresh_cookie(response, issued, settings)
    return ok(issued.session)


@router.post(ep.AUTH_REFRESH, dependencies=[RateLimit], response_model=Envelope[AuthSession])
async def refresh(
    request: Request, response: Response, service: Service, settings: AppSettings
) -> Envelope[AuthSession] | JSONResponse:
    try:
        issued = await service.refresh(request.cookies.get(REFRESH_COOKIE), client_info(request))
    except SessionRejected as rejected:
        if rejected.reason == "REUSE_DETECTED":
            logger.warning(
                "refresh token reuse detected - session family revoked",
                extra={"context": {"ip": request.client.host if request.client else None}},
            )
        # Return (not raise) the 401: raising would roll back the request's transaction
        # and undo the family revocation the service just made.
        rejection = JSONResponse(
            status_code=rejected.status_code, content=fail_body(rejected.code, rejected.message)
        )
        _clear_refresh_cookie(rejection, settings)
        return rejection
    _set_refresh_cookie(response, issued, settings)
    return ok(issued.session)


@router.post(ep.AUTH_SIGN_OUT, response_model=Envelope[SignedOut])
async def sign_out(
    request: Request, response: Response, service: Service, settings: AppSettings
) -> Envelope[SignedOut]:
    await service.sign_out(request.cookies.get(REFRESH_COOKIE))
    _clear_refresh_cookie(response, settings)
    return ok(SignedOut())


@router.get(ep.AUTH_SESSION, response_model=Envelope[CurrentUserResponse])
async def current_session(
    user_id: CurrentUserId, service: Service
) -> Envelope[CurrentUserResponse]:
    user = await service.get_user(user_id)
    return ok(CurrentUserResponse(user=to_auth_user(user)))
