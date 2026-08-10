# SPDX-License-Identifier: AGPL-3.0-only
"""Forced sleeptime summary template (gist / tags / lesson_family)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class SummarySlots:
    gist: str
    tags: tuple[str, ...] = ()
    lesson_family: Optional[str] = None


TEMPLATE = """GIST: {gist}
TAGS: {tags}
LESSON_FAMILY: {lesson_family}"""


def format_summary(slots: SummarySlots) -> str:
    """Render the sleeptime summary template from structured slots."""
    gist = (slots.gist or "").strip() or "(empty)"
    tags = ", ".join(t.strip() for t in slots.tags if t and t.strip()) or "(none)"
    lf = (slots.lesson_family or "").strip() or "(none)"
    return TEMPLATE.format(gist=gist, tags=tags, lesson_family=lf)


def parse_summary(text: str) -> SummarySlots:
    """Best-effort parse of a templated summary back into slots."""
    gist = ""
    tags: list[str] = []
    lesson_family: Optional[str] = None
    for line in (text or "").splitlines():
        line = line.strip()
        if line.upper().startswith("GIST:"):
            gist = line.split(":", 1)[1].strip()
        elif line.upper().startswith("TAGS:"):
            raw = line.split(":", 1)[1].strip()
            if raw and raw != "(none)":
                tags = [t.strip() for t in raw.split(",") if t.strip()]
        elif line.upper().startswith("LESSON_FAMILY:"):
            raw = line.split(":", 1)[1].strip()
            if raw and raw != "(none)":
                lesson_family = raw
    return SummarySlots(gist=gist, tags=tuple(tags), lesson_family=lesson_family)


def coerce_summary(
    gist: str,
    *,
    tags: Sequence[str] = (),
    lesson_family: Optional[str] = None,
) -> str:
    """Convenience: build template string from loose args."""
    return format_summary(
        SummarySlots(gist=gist, tags=tuple(tags), lesson_family=lesson_family)
    )
