"""Build the job board(s) the Job Search agent uses, from settings."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.jobs.adzuna import AdzunaJobBoard
from app.jobs.jobicy import JobicyJobBoard
from app.jobs.multi import ClosableJobBoard, MultiJobBoard
from app.jobs.remotive import RemotiveJobBoard


def build_job_board(
    settings: Settings, transport: httpx.AsyncBaseTransport | None = None
) -> ClosableJobBoard | None:
    """Free boards from JOB_BOARDS, plus Adzuna when its keys are set. None = no live search."""
    boards: list[ClosableJobBoard] = []
    if settings.adzuna_app_id and settings.adzuna_app_key.get_secret_value():
        # First: it's the only one that searches local (non-remote) jobs by city.
        boards.append(
            AdzunaJobBoard(
                app_id=settings.adzuna_app_id,
                app_key=settings.adzuna_app_key.get_secret_value(),
                country=settings.jobs_country,
                transport=transport,
            )
        )
    for name in settings.job_boards:
        if name == "jobicy":
            boards.append(JobicyJobBoard(transport=transport))
        elif name == "remotive":
            boards.append(RemotiveJobBoard(transport=transport))
    if not boards:
        return None
    return boards[0] if len(boards) == 1 else MultiJobBoard(boards)
