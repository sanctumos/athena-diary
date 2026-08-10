# SPDX-License-Identifier: AGPL-3.0-only
"""Idempotent schema migrations for the Athena diary SQLite DB."""

from __future__ import annotations

import sqlite3
from typing import Callable, List, Tuple

Migration = Tuple[int, str, Callable[[sqlite3.Connection], None]]


def _m1_core(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            body TEXT NOT NULL,
            summary TEXT,
            sensitivity_note TEXT,
            source TEXT NOT NULL DEFAULT 'hot_turn',
            run_id TEXT,
            message_id TEXT,
            lesson_family_id INTEGER,
            sleeptime_processed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS entry_tags (
            entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (entry_id, tag_id)
        );

        CREATE TABLE IF NOT EXISTS lesson_families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT
        );

        CREATE TABLE IF NOT EXISTS see_also (
            entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            related_entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            PRIMARY KEY (entry_id, related_entry_id),
            CHECK (entry_id != related_entry_id)
        );

        -- Blob fallback embeddings (always present). sqlite-vec vec0 is optional.
        CREATE TABLE IF NOT EXISTS embeddings (
            entry_id INTEGER PRIMARY KEY REFERENCES entries(id) ON DELETE CASCADE,
            model TEXT NOT NULL,
            provider TEXT NOT NULL,
            dim INTEGER NOT NULL,
            vector BLOB NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_entries_sleeptime
            ON entries(sleeptime_processed_at);
        CREATE INDEX IF NOT EXISTS idx_entries_lesson_family
            ON entries(lesson_family_id);
        """
    )
    # FTS5 — content-sync with entries
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='diary_fts'"
    ).fetchone()
    if not row:
        conn.executescript(
            """
            CREATE VIRTUAL TABLE diary_fts USING fts5(
                body,
                summary,
                content='entries',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
              INSERT INTO diary_fts(rowid, body, summary)
              VALUES (new.id, new.body, coalesce(new.summary, ''));
            END;

            CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
              INSERT INTO diary_fts(diary_fts, rowid, body, summary)
              VALUES ('delete', old.id, old.body, coalesce(old.summary, ''));
            END;

            CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
              INSERT INTO diary_fts(diary_fts, rowid, body, summary)
              VALUES ('delete', old.id, old.body, coalesce(old.summary, ''));
              INSERT INTO diary_fts(rowid, body, summary)
              VALUES (new.id, new.body, coalesce(new.summary, ''));
            END;
            """
        )


MIGRATIONS: List[Migration] = [
    (1, "core_tables_fts_embeddings", _m1_core),
]


def applied_versions(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {int(r[0]) for r in rows}


def apply_migrations(conn: sqlite3.Connection) -> list[int]:
    """Apply pending migrations; safe to call repeatedly. Returns newly applied versions."""
    done = applied_versions(conn)
    newly: list[int] = []
    for version, _name, fn in MIGRATIONS:
        if version in done:
            continue
        fn(conn)
        conn.execute(
            "INSERT INTO schema_migrations(version) VALUES (?)",
            (version,),
        )
        newly.append(version)
    conn.commit()
    return newly
