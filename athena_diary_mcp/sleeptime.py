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
    get_entry,
    list_processed,
    list_unprocessed,
    set_entry_tags,
    update_entry_clerk,
)
from .summary import coerce_summary
from .vector_index import embed_and_store, search_similar

# Optional LLM-shaped hook: (entry) -> (gist, tags, lesson_family_slug)
ClerkAnnotator = Callable[[Entry], tuple[str, Sequence[str], Optional[str]]]

# Thematic / same-thread linking (not only near-duplicate summaries).
DEFAULT_SEE_ALSO_MIN_SCORE = 0.6

_EXPLICIT_ENTRY_RE = re.compile(
    r"(?:\bentry\b|\bentries\b|#)\s*(\d+)"
    r"|\bcorrection\s+to\s+(\d+)"
    r"|\brevisits?\s+entry\s+(\d+)",
    re.IGNORECASE,
)


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


def explicit_entry_refs(body: str) -> tuple[int, ...]:
    """Entry ids cited in prose (entry 35, #35, correction to 35, …)."""
    seen: set[int] = set()
    out: list[int] = []
    for match in _EXPLICIT_ENTRY_RE.finditer(body or ""):
        for group in match.groups():
            if not group:
                continue
            eid = int(group)
            if eid not in seen:
                seen.add(eid)
                out.append(eid)
    return tuple(out)


@dataclass(frozen=True)
class ClerkResult:
    processed: int
    entry_ids: tuple[int, ...]
    skipped_already_done: int = 0


@dataclass(frozen=True)
class RelinkResult:
    scanned: int
    entry_ids: tuple[int, ...]
    links_added: int


def link_see_also_for_entry(
    conn: sqlite3.Connection,
    entry: Entry,
    *,
    provider: EmbedProvider,
    min_score: float = DEFAULT_SEE_ALSO_MIN_SCORE,
    neighbor_limit: int = 8,
) -> int:
    """
    Wire see_also for one entry: explicit body refs + semantic neighbors on summary/body.

    Returns count of link operations attempted (INSERT OR IGNORE may noop duplicates).
    """
    added = 0
    for ref_id in explicit_entry_refs(entry.body):
        if ref_id == entry.id:
            continue
        try:
            get_entry(conn, ref_id)
        except Exception:
            continue
        add_see_also(conn, entry.id, ref_id)
        added += 1

    query_text = (entry.summary or entry.body or "").strip()
    if not query_text:
        return added

    neighbors = search_similar(
        conn,
        query_text,
        limit=neighbor_limit,
        provider=provider,
        min_score=min_score,
    )
    for hit in neighbors:
        if hit.id != entry.id:
            add_see_also(conn, entry.id, hit.id)
            added += 1

    # Body fallback when summary alone missed thematic siblings
    body = (entry.body or "").strip()
    if body and body != query_text:
        body_neighbors = search_similar(
            conn,
            body[:1200],
            limit=neighbor_limit,
            provider=provider,
            min_score=min_score,
        )
        for hit in body_neighbors:
            if hit.id != entry.id:
                add_see_also(conn, entry.id, hit.id)
                added += 1

    return added


def sleeptime_pass(
    conn: sqlite3.Connection,
    *,
    limit: int = 10,
    provider: Optional[EmbedProvider] = None,
    annotator: Optional[ClerkAnnotator] = None,
    dedupe_min_score: float = DEFAULT_SEE_ALSO_MIN_SCORE,
) -> ClerkResult:
    """
    Process up to ``limit`` unprocessed entries: template summary, tags,
    lesson_family, see_also (related entries), re-embed, stamp processed.

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
        refreshed = get_entry(conn, entry.id)
        link_see_also_for_entry(
            conn, refreshed, provider=prov, min_score=dedupe_min_score
        )
        done_ids.append(entry.id)

    return ClerkResult(processed=len(done_ids), entry_ids=tuple(done_ids))


def see_also_relink_pass(
    conn: sqlite3.Connection,
    *,
    limit: int = 25,
    provider: Optional[EmbedProvider] = None,
    min_score: float = DEFAULT_SEE_ALSO_MIN_SCORE,
) -> RelinkResult:
    """
    Re-scan processed entries and add see_also crosslinks (idempotent).

    Does not rewrite summaries or re-stamp sleeptime_processed_at. Use after lowering
    the similarity threshold or when older entries were processed before links existed.
    """
    n = max(1, int(limit))
    prov = provider or get_embed_provider()
    batch = list(list_processed(conn, limit=n))
    total_links = 0
    scanned: List[int] = []

    for entry in batch:
        total_links += link_see_also_for_entry(
            conn, entry, provider=prov, min_score=min_score
        )
        scanned.append(entry.id)

    return RelinkResult(
        scanned=len(scanned),
        entry_ids=tuple(scanned),
        links_added=total_links,
    )
