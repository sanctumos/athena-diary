# SPDX-License-Identifier: AGPL-3.0-only
"""Sleeptime clerk — batch process untagged/backlog diary entries."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from .embeddings import EmbedProvider, get_embed_provider
from .store import (
    Entry,
    add_see_also,
    ensure_lesson_family,
    list_unprocessed,
    set_entry_tags,
    update_entry_clerk,
)
from .summary import coerce_summary
from .vector_index import embed_and_store, search_similar

# Optional LLM-shaped hook: (entry) -> (gist, tags, lesson_family_slug)
ClerkAnnotator = Callable[[Entry], tuple[str, Sequence[str], Optional[str]]]


def default_annotator(entry: Entry) -> tuple[str, Sequence[str], Optional[str]]:
    """
    Deterministic offline annotator (no network).

    Gist = first ~160 chars of body; tags = alphanumeric tokens length>=4 (max 5);
    lesson_family = first tag or 'general'.
    """
    body = (entry.body or "").strip()
    gist = body[:160] + ("…" if len(body) > 160 else "")
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", body.lower())
    # Preserve order, unique
    seen: set[str] = set()
    tags: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            tags.append(t)
        if len(tags) >= 5:
            break
    if not tags:
        tags = ["untagged"]
    lesson = tags[0] if tags else "general"
    return gist or "(empty)", tags, lesson


@dataclass(frozen=True)
class ClerkResult:
    processed: int
    entry_ids: tuple[int, ...]
    skipped_already_done: int = 0


def sleeptime_pass(
    conn: sqlite3.Connection,
    *,
    limit: int = 10,
    provider: Optional[EmbedProvider] = None,
    annotator: Optional[ClerkAnnotator] = None,
    dedupe_min_score: float = 0.92,
) -> ClerkResult:
    """
    Process up to ``limit`` unprocessed entries: template summary, tags,
    lesson_family, see_also (near-dupes), re-embed, stamp processed.

    Idempotent: entries with sleeptime_processed_at set are not selected again.
    """
    n = max(1, int(limit))
    pending = list(list_unprocessed(conn, limit=n))
    if not pending:
        return ClerkResult(processed=0, entry_ids=())

    prov = provider or get_embed_provider()
    ann = annotator or default_annotator
    done_ids: List[int] = []

    for entry in pending:
        gist, tags, lesson_slug = ann(entry)
        summary = coerce_summary(gist, tags=tags, lesson_family=lesson_slug)
        lf_id = ensure_lesson_family(conn, lesson_slug or "general")
        set_entry_tags(conn, entry.id, tags)
        update_entry_clerk(
            conn,
            entry.id,
            summary=summary,
            lesson_family_id=lf_id,
            mark_processed=True,
        )
        embed_and_store(conn, entry.id, summary, provider=prov)

        # Dedupe clusters: link see_also to near-duplicate summaries
        neighbors = search_similar(
            conn,
            summary,
            limit=5,
            provider=prov,
            min_score=dedupe_min_score,
        )
        for hit in neighbors:
            if hit.id != entry.id:
                add_see_also(conn, entry.id, hit.id)

        done_ids.append(entry.id)

    return ClerkResult(processed=len(done_ids), entry_ids=tuple(done_ids))
