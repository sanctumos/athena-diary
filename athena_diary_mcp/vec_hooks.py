# SPDX-License-Identifier: AGPL-3.0-only
"""Optional sqlite-vec wiring. Falls back to embeddings BLOB table when unavailable."""

from __future__ import annotations

import sqlite3
from typing import Optional


def sqlite_vec_available() -> bool:
    try:
        import sqlite_vec  # noqa: F401

        return True
    except ImportError:
        return False


def try_load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec extension into connection if installed. Returns True on success."""
    if not sqlite_vec_available():
        return False
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except (AttributeError, sqlite3.Error, OSError):
        # Android / stripped libsqlite often cannot load extensions.
        return False


def ensure_vec0(conn: sqlite3.Connection, dimensions: int = 8) -> Optional[str]:
    """
    Ensure a vec0 virtual table exists when sqlite-vec is loadable.

    Returns table name or None if sqlite-vec is not available (BLOB embeddings still work).
    Dimensions are fixed at create time for vec0 — callers should use a consistent dim.
    """
    if not try_load_sqlite_vec(conn):
        return None
    name = "diary_summary_vec"
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    if not exists:
        conn.execute(
            f"""
            CREATE VIRTUAL TABLE {name} USING vec0(
                entry_id INTEGER PRIMARY KEY,
                embedding float[{int(dimensions)}]
            )
            """
        )
        conn.commit()
    return name
