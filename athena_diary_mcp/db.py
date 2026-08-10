# SPDX-License-Identifier: AGPL-3.0-only
"""SQLite connection helpers — WAL, foreign keys, migration apply."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

from .migrations import apply_migrations

DEFAULT_DB_NAME = "athena-diary.db"


def default_db_path() -> Path:
    env = os.environ.get("DIARY_DB")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.cwd() / "db" / DEFAULT_DB_NAME).resolve()


def connect(db_path: Optional[os.PathLike[str] | str] = None) -> sqlite3.Connection:
    """Open diary DB with WAL + FKs; apply idempotent migrations."""
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    apply_migrations(conn)
    return conn
