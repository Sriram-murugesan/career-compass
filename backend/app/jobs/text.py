"""Small text helpers shared by the job-board adapters."""

from __future__ import annotations

import html
import re

_TAG = re.compile(r"<[^>]+>")


def clean_html(value: object, limit: int | None = None) -> str:
    """Strip tags, unescape entities, collapse whitespace; optionally truncate."""
    text = " ".join(html.unescape(_TAG.sub(" ", str(value or ""))).split())
    return text[:limit] if limit is not None else text
