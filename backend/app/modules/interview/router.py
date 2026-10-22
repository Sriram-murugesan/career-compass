"""HTTP LAYER for mock interview tests."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app import endpoints as ep
from app.core.responses import Envelope, ok
from app.modules.auth import CurrentUserId
from app.modules.interview.dependencies import get_interview_service
from app.modules.interview.schemas import (
    AttemptIn,
    AttemptResult,
    MockTestCreate,
    MockTestOut,
    MockTestSummary,
)
from app.modules.interview.service import InterviewService

router = APIRouter(tags=["interview"])

Service = Annotated[InterviewService, Depends(get_interview_service)]


@router.post(ep.INTERVIEW_MOCK_TESTS, response_model=Envelope[MockTestOut], status_code=201)
async def create_mock_test(
    body: MockTestCreate, user_id: CurrentUserId, service: Service
) -> Envelope[MockTestOut]:
    return ok(await service.create(user_id, body))


@router.get(ep.INTERVIEW_MOCK_TESTS, response_model=Envelope[list[MockTestSummary]])
async def list_mock_tests(
    user_id: CurrentUserId, service: Service
) -> Envelope[list[MockTestSummary]]:
    return ok(await service.list_tests(user_id))


@router.get(ep.INTERVIEW_MOCK_TEST, response_model=Envelope[MockTestOut])
async def get_mock_test(
    test_id: uuid.UUID, user_id: CurrentUserId, service: Service
) -> Envelope[MockTestOut]:
    return ok(await service.get(user_id, test_id))


@router.post(
    ep.INTERVIEW_MOCK_TEST_ATTEMPTS, response_model=Envelope[AttemptResult], status_code=201
)
async def submit_mock_test(
    test_id: uuid.UUID, body: AttemptIn, user_id: CurrentUserId, service: Service
) -> Envelope[AttemptResult]:
    return ok(await service.submit(user_id, test_id, body))
