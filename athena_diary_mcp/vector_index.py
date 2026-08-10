# SPDX-License-Identifier: AGPL-3.0-only
"""Persist summary embeddings (BLOB always; sqlite-vec when loadable) + KNN."""

from __future__ import annotations

import math
import sqlite3
import struct
from typing import List, Optional, Sequence

from .embeddings import EmbedProvider, EmbedResult, get_embed_provider
from .search import SearchHit, _tags_for, search_fts
from .store import get_entry
from .vec_hooks import ensure_vec0


def pack_vector(vec: Sequence[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *[float(x) for x in vec])


def unpack_vector(blob: bytes) -> tuple[float, ...]:
    n = len(blob) // 4
    return struct.unpack(f"{n}f", blob)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def store_embedding(
    conn: sqlite3.Connection,
    entry_id: int,
    result: EmbedResult,
) -> None:
    """Upsert BLOB embedding; mirror into vec0 when available."""
    get_entry(conn, entry_id)
    blob = pack_vector(result.vector)
    conn.execute(
        """
        INSERT INTO embeddings(entry_id, model, provider, dim, vector, updated_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(entry_id) DO UPDATE SET
          model=excluded.model,
          provider=excluded.provider,
          dim=excluded.dim,
          vector=excluded.vector,
          updated_at=datetime('now')
        """,
        (entry_id, result.model, result.provider, result.dim, blob),
    )
    table = ensure_vec0(conn, dimensions=result.dim)
    if table:
        # vec0 upsert: delete + insert
        try:
            conn.execute(f"DELETE FROM {table} WHERE entry_id = ?", (entry_id,))
            conn.execute(
                f"INSERT INTO {table}(entry_id, embedding) VALUES (?, ?)",
                (entry_id, list(result.vector)),
            )
        except sqlite3.Error:
            pass  # BLOB path remains authoritative
    conn.commit()


def embed_and_store(
    conn: sqlite3.Connection,
    entry_id: int,
    text: str,
    *,
    provider: Optional[EmbedProvider] = None,
) -> EmbedResult:
    prov = provider or get_embed_provider()
    result = prov.embed([text or ""])[0]
    store_embedding(conn, entry_id, result)
    return result


def search_similar(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    provider: Optional[EmbedProvider] = None,
    min_score: float = 0.15,
) -> List[SearchHit]:
    """
    KNN over stored summary embeddings (BLOB cosine; vec0 when present).

    Ranking: prefer vec/BLOB hits; FTS is layered by search_diary.
    """
    if not (query or "").strip():
        return []
    lim = max(1, int(limit))
    prov = provider or get_embed_provider()
    qvec = prov.embed([query])[0].vector

    # Prefer sqlite-vec KNN when table exists and extension loaded
    table = ensure_vec0(conn, dimensions=len(qvec))
    if table:
        try:
            rows = conn.execute(
                f"""
                SELECT entry_id, distance
                FROM {table}
                WHERE embedding MATCH ?
                ORDER BY distance
                LIMIT ?
                """,
                (list(qvec), lim),
            ).fetchall()
            ids = [int(r["entry_id"]) for r in rows]
            return _hits_from_ids(conn, ids, rank="vec")
        except sqlite3.Error:
            pass

    # BLOB cosine fallback
    rows = conn.execute(
        "SELECT entry_id, dim, vector FROM embeddings"
    ).fetchall()
    scored: list[tuple[float, int]] = []
    for r in rows:
        vec = unpack_vector(r["vector"])
        if len(vec) != len(qvec):
            continue
        score = cosine(qvec, vec)
        if score >= min_score:
            scored.append((score, int(r["entry_id"])))
    scored.sort(key=lambda t: t[0], reverse=True)
    ids = [eid for _, eid in scored[:lim]]
    return _hits_from_ids(conn, ids, rank="vec")


def _hits_from_ids(
    conn: sqlite3.Connection, ids: Sequence[int], *, rank: str
) -> List[SearchHit]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""
        SELECT id, summary, created_at, source FROM entries
        WHERE id IN ({placeholders})
        """,
        tuple(ids),
    ).fetchall()
    by_id = {int(r["id"]): r for r in rows}
    tag_map = _tags_for(conn, list(ids))
    out: List[SearchHit] = []
    for eid in ids:
        r = by_id.get(eid)
        if not r:
            continue
        out.append(
            SearchHit(
                id=eid,
                summary=r["summary"],
                created_at=str(r["created_at"]),
                source=str(r["source"]),
                rank=rank,
                tags=tag_map.get(eid, ()),
            )
        )
    return out


def search_diary(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    provider: Optional[EmbedProvider] = None,
) -> List[SearchHit]:
    """
    Combined diary search.

    Ranking: prefer vector hits first, then fill remaining slots from FTS.
    FTS always available as fail-open path when vectors are missing/weak.
    """
    lim = max(1, int(limit))
    vec_hits = search_similar(conn, query, limit=lim, provider=provider)
    seen = {h.id for h in vec_hits}
    fts_hits = search_fts(conn, query, limit=lim)
    merged: List[SearchHit] = list(vec_hits)
    for h in fts_hits:
        if h.id not in seen:
            merged.append(h)
            seen.add(h.id)
        if len(merged) >= lim:
            break
    return merged[:lim]
