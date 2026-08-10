# SPDX-License-Identifier: AGPL-3.0-only
"""FTS diary search (keyword path; semantic merge lands with vec slice)."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class SearchHit:
    id: int
    summary: Optional[str]
    created_at: str
    source: str
    rank: str  # "fts" | "tag" | "vec"
    tags: tuple[str, ...] = ()


def sanitize_fts_query(q: str) -> str:
    """Turn free text into a safe FTS5 MATCH query (AND of tokens)."""
    tokens = re.findall(r"[A-Za-z0-9_]+", q or "")
    if not tokens:
        return ""
    return " ".join(tokens)


def _tags_for(conn: sqlite3.Connection, entry_ids: Sequence[int]) -> dict[int, tuple[str, ...]]:
    if not entry_ids:
        return {}
    placeholders = ",".join("?" * len(entry_ids))
    rows = conn.execute(
        f"""
        SELECT et.entry_id, t.name
        FROM entry_tags et
        JOIN tags t ON t.id = et.tag_id
        WHERE et.entry_id IN ({placeholders})
        ORDER BY t.name
        """,
        tuple(entry_ids),
    ).fetchall()
    out: dict[int, list[str]] = {int(i): [] for i in entry_ids}
    for r in rows:
        out[int(r["entry_id"])].append(str(r["name"]))
    return {k: tuple(v) for k, v in out.items()}


def search_fts(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
) -> List[SearchHit]:
    """Search body/summary via FTS5; also match tag names. Returns ids + summaries (not bodies)."""
    q = sanitize_fts_query(query)
    if not q:
        return []
    lim = max(1, int(limit))
    seen: dict[int, SearchHit] = {}

    fts_rows = conn.execute(
        """
        SELECT e.id, e.summary, e.created_at, e.source
        FROM diary_fts
        JOIN entries e ON e.id = diary_fts.rowid
        WHERE diary_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (q, lim),
    ).fetchall()
    for r in fts_rows:
        eid = int(r["id"])
        seen[eid] = SearchHit(
            id=eid,
            summary=r["summary"],
            created_at=str(r["created_at"]),
            source=str(r["source"]),
            rank="fts",
        )

    # Tag name matches (fail-open keyword path when FTS misses tags-only queries)
    like = f"%{q.split()[0]}%" if q else ""
    if like:
        tag_rows = conn.execute(
            """
            SELECT DISTINCT e.id, e.summary, e.created_at, e.source
            FROM entries e
            JOIN entry_tags et ON et.entry_id = e.id
            JOIN tags t ON t.id = et.tag_id
            WHERE t.name LIKE ? COLLATE NOCASE
            ORDER BY e.id DESC
            LIMIT ?
            """,
            (like, lim),
        ).fetchall()
        for r in tag_rows:
            eid = int(r["id"])
            if eid not in seen:
                seen[eid] = SearchHit(
                    id=eid,
                    summary=r["summary"],
                    created_at=str(r["created_at"]),
                    source=str(r["source"]),
                    rank="tag",
                )

    ids = list(seen.keys())[:lim]
    tag_map = _tags_for(conn, ids)
    out: List[SearchHit] = []
    for eid in ids:
        h = seen[eid]
        out.append(
            SearchHit(
                id=h.id,
                summary=h.summary,
                created_at=h.created_at,
                source=h.source,
                rank=h.rank,
                tags=tag_map.get(eid, ()),
            )
        )
    return out[:lim]


def search_diary(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
) -> List[SearchHit]:
    """Keyword search via FTS (+ tags). Semantic merge lands with embeddings/vec slice."""
    return search_fts(conn, query, limit=limit)
