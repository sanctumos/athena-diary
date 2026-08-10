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
