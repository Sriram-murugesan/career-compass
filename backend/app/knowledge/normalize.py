"""Turn free text (profile entries, posting titles) into stable graph keys.

Two users typing "ReactJS" and "react.js" must land on the same node, and a posting
titled "Senior Frontend Engineer - UK" must meet a user targeting "Frontend Engineer".
"""

from __future__ import annotations

import re

_SPACES = re.compile(r"\s+")
_EDGE_PUNCT = " .,;:!?/\\-_'\"()[]{}"
# Posting titles carry region / team suffixes: "… - UK", "… | Remote", "… (Contract)"
_DASHES = "-" + chr(0x2013) + chr(0x2014)  # hyphen, en dash, em dash
_TITLE_SUFFIX = re.compile(rf"\s+(?:[{_DASHES}|/]|\(|\bat\b).*$", re.IGNORECASE)
_SENIORITY = re.compile(
    r"^(?:senior|sr\.?|junior|jr\.?|lead|staff|principal|mid(?:-level)?|associate|"
    r"intern|entry[- ]level|head of|trainee)\s+",
    re.IGNORECASE,
)

SKILL_ALIASES = {
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    "js": "javascript",
    "ts": "typescript",
    "nextjs": "next.js",
    "next js": "next.js",
    "node": "node.js",
    "nodejs": "node.js",
    "node js": "node.js",
    "vuejs": "vue",
    "vue.js": "vue",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "golang": "go",
    "py": "python",
    "tailwind": "tailwind css",
    "tailwindcss": "tailwind css",
    "ml": "machine learning",
    "aws cloud": "aws",
}


def _clean(text: str) -> str:
    return _SPACES.sub(" ", text).strip(_EDGE_PUNCT).strip()


def skill_key(text: str) -> str:
    key = _clean(text).lower()
    return SKILL_ALIASES.get(key, key)[:120]


def role_label(text: str) -> str:
    """ "Senior Frontend Engineer - UK" → "Frontend Engineer" (seniority and suffixes dropped)."""
    title = _TITLE_SUFFIX.sub("", _clean(text))
    previous = None
    while previous != title:  # "Senior Lead …" → strip repeatedly
        previous = title
        title = _SENIORITY.sub("", title)
    return _clean(title)[:120]


def role_key(text: str) -> str:
    return role_label(text).lower()


def company_key(text: str) -> str:
    key = _clean(text).lower()
    # Longest first, so " pvt ltd" wins over " ltd".
    for suffix in (" private limited", " pvt ltd", " limited", " gmbh", " inc", " llc", " ltd"):
        if key.endswith(suffix):
            key = key[: -len(suffix)].rstrip(" ,")
            break
    return key[:120]


def current_role_from_headline(headline: str) -> str:
    """ "Frontend developer, 3 years" → "frontend developer"; "" if it doesn't look like a role."""
    first = re.split(rf"[,|@·•]|\s[{_DASHES}]\s|\bat\b", headline, maxsplit=1)[0]
    label = role_label(first)
    if not label or len(label.split()) > 6 or any(ch.isdigit() for ch in label):
        return ""
    return label
