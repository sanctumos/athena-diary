# SPDX-License-Identifier: AGPL-3.0-only
"""Diary entry write / get / domain types."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence


class DiaryError(ValueError):
    """Domain error for diary operations."""


@dataclass(frozen=True)
class Entry:
    id: int
    body: str
    summary: Optional[str]
    sensitivity_note: Optional[str]
    source: str
    created_at: str
    updated_at: str
    run_id: Optional[str] = None
    message_id: Optional[str] = None
    lesson_family_id: Optional[int] = None
    sleeptime_processed_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Entry":
        return cls(
            id=int(row["id"]),
            body=str(row["body"]),
            summary=row["summary"],
            sensitivity_note=row["sensitivity_note"],
            source=str(row["source"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            run_id=row["run_id"],
            message_id=row["message_id"],
            lesson_family_id=row["lesson_family_id"],
            sleeptime_processed_at=row["sleeptime_processed_at"],
        )


_ENTRY_COLS = (
    "id, body, summary, sensitivity_note, source, created_at, updated_at, "
    "run_id, message_id, lesson_family_id, sleeptime_processed_at"
)


def write_entry(
    conn: sqlite3.Connection,
    body: str,
    *,
    summary: Optional[str] = None,
    sensitivity_note: Optional[str] = None,
    source: str = "hot_turn",
    run_id: Optional[str] = None,
    message_id: Optional[str] = None,
) -> Entry:
    """Append a diary entry. Raises DiaryError if body is empty/whitespace."""
    text = (body or "").strip()
    if not text:
        raise DiaryError("body must be non-empty")
    cur = conn.execute(
        """
        INSERT INTO entries(body, summary, sensitivity_note, source, run_id, message_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            text,
            summary,
            sensitivity_note,
            source or "hot_turn",
            run_id,
            message_id,
        ),
    )
    conn.commit()
    return get_entry(conn, int(cur.lastrowid))


def get_entry(conn: sqlite3.Connection, entry_id: int) -> Entry:
    row = conn.execute(
        f"SELECT {_ENTRY_COLS} FROM entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if row is None:
        raise DiaryError(f"entry not found: {entry_id}")
    return Entry.from_row(row)


def list_unprocessed(conn: sqlite3.Connection, limit: int = 50) -> Sequence[Entry]:
    rows = conn.execute(
        f"""
        SELECT {_ENTRY_COLS} FROM entries
        WHERE sleeptime_processed_at IS NULL
        ORDER BY id ASC
        LIMIT ?
        """,
        (max(1, int(limit)),),
    ).fetchall()
    return [Entry.from_row(r) for r in rows]


def ensure_tag(conn: sqlite3.Connection, name: str) -> int:
    """Insert tag if missing; return tag id."""
    clean = (name or "").strip().lower()
    if not clean:
        raise DiaryError("tag name must be non-empty")
    conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (clean,))
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (clean,)).fetchone()
    assert row is not None
    conn.commit()
    return int(row["id"])


def set_entry_tags(conn: sqlite3.Connection, entry_id: int, names: Sequence[str]) -> tuple[str, ...]:
    """Replace tags on an entry. Returns normalized tag names."""
    get_entry(conn, entry_id)  # raises if missing
    conn.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))
    out: list[str] = []
    for raw in names:
        clean = (raw or "").strip().lower()
        if not clean:
            continue
        tid = ensure_tag(conn, clean)
        conn.execute(
            "INSERT OR IGNORE INTO entry_tags(entry_id, tag_id) VALUES (?, ?)",
            (entry_id, tid),
        )
        out.append(clean)
    conn.commit()
    return tuple(sorted(set(out)))


def ensure_lesson_family(
    conn: sqlite3.Connection, slug: str, *, title: Optional[str] = None
) -> int:
    clean = (slug or "").strip().lower().replace(" ", "-")
    if not clean:
        raise DiaryError("lesson_family slug must be non-empty")
    conn.execute(
        "INSERT OR IGNORE INTO lesson_families(slug, title) VALUES (?, ?)",
        (clean, title or clean),
    )
    row = conn.execute(
        "SELECT id FROM lesson_families WHERE slug = ?", (clean,)
    ).fetchone()
    assert row is not None
    conn.commit()
    return int(row["id"])


def update_entry_clerk(
    conn: sqlite3.Connection,
    entry_id: int,
    *,
    summary: str,
    lesson_family_id: Optional[int] = None,
    mark_processed: bool = True,
) -> Entry:
    """Rewrite summary / lesson_family and optionally stamp sleeptime_processed_at."""
    get_entry(conn, entry_id)
    if mark_processed:
        conn.execute(
            """
            UPDATE entries SET
              summary = ?,
              lesson_family_id = ?,
              sleeptime_processed_at = datetime('now'),
              updated_at = datetime('now')
            WHERE id = ?
            """,
            (summary, lesson_family_id, entry_id),
        )
    else:
        conn.execute(
            """
            UPDATE entries SET
              summary = ?,
              lesson_family_id = ?,
              updated_at = datetime('now')
            WHERE id = ?
            """,
            (summary, lesson_family_id, entry_id),
        )
    conn.commit()
    return get_entry(conn, entry_id)


def add_see_also(
    conn: sqlite3.Connection, entry_id: int, related_entry_id: int
) -> None:
    if entry_id == related_entry_id:
        return
    # Store both directions for easy lookup
    for a, b in ((entry_id, related_entry_id), (related_entry_id, entry_id)):
        conn.execute(
            "INSERT OR IGNORE INTO see_also(entry_id, related_entry_id) VALUES (?, ?)",
            (a, b),
        )
    conn.commit()


def list_see_also(conn: sqlite3.Connection, entry_id: int) -> Sequence[int]:
    rows = conn.execute(
        "SELECT related_entry_id FROM see_also WHERE entry_id = ? ORDER BY related_entry_id",
        (entry_id,),
    ).fetchall()
    return [int(r["related_entry_id"]) for r in rows]


def list_entry_tags(conn: sqlite3.Connection, entry_id: int) -> tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT t.name
        FROM entry_tags et
        JOIN tags t ON t.id = et.tag_id
        WHERE et.entry_id = ?
        ORDER BY t.name
        """,
        (entry_id,),
    ).fetchall()
    return tuple(str(r["name"]) for r in rows)


def get_lesson_family_slug(
    conn: sqlite3.Connection, lesson_family_id: Optional[int]
) -> Optional[str]:
    if lesson_family_id is None:
        return None
    row = conn.execute(
        "SELECT slug FROM lesson_families WHERE id = ?",
        (int(lesson_family_id),),
    ).fetchone()
    return str(row["slug"]) if row is not None else None


def entry_detail(conn: sqlite3.Connection, entry: Entry) -> dict[str, Any]:
    """Entry row plus cross-refs and clerk metadata for MCP responses."""
    return {
        "id": entry.id,
        "body": entry.body,
        "summary": entry.summary,
        "sensitivity_note": entry.sensitivity_note,
        "source": entry.source,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "run_id": entry.run_id,
        "message_id": entry.message_id,
        "lesson_family_id": entry.lesson_family_id,
        "lesson_family_slug": get_lesson_family_slug(conn, entry.lesson_family_id),
        "sleeptime_processed_at": entry.sleeptime_processed_at,
        "tags": list(list_entry_tags(conn, entry.id)),
        "see_also_entry_ids": list(list_see_also(conn, entry.id)),
    }
