"""Tests for diary schema migrations and db connect."""

import sqlite3
from pathlib import Path

import pytest

from athena_diary_mcp.db import connect, default_db_path
from athena_diary_mcp.migrations import apply_migrations, applied_versions
from athena_diary_mcp import vec_hooks


def test_default_db_path_respects_env(tmp_path, monkeypatch):
    target = tmp_path / "custom.db"
    monkeypatch.setenv("DIARY_DB", str(target))
    assert default_db_path() == target.resolve()


def test_default_db_path_without_env(monkeypatch, tmp_path):
    monkeypatch.delenv("DIARY_DB", raising=False)
    monkeypatch.chdir(tmp_path)
    p = default_db_path()
    assert p.name == "athena-diary.db"
    assert p.parent.name == "db"


def test_migrations_idempotent(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    first = apply_migrations(conn)
    assert 1 in first
    second = apply_migrations(conn)
    assert second == []
    assert applied_versions(conn) == {1}
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )
    }
    assert "entries" in tables
    assert "diary_fts" in tables
    assert "embeddings" in tables
    conn.close()


def test_connect_roundtrip_insert_fts(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "diary.db"))
    conn = connect()
    cur = conn.execute(
        "INSERT INTO entries(body, summary, source) VALUES (?,?,?)",
        ("hello diary world", "hello gist", "hot_turn"),
    )
    eid = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT body, summary FROM entries WHERE id=?", (eid,)).fetchone()
    assert row["body"] == "hello diary world"
    hits = conn.execute(
        "SELECT rowid FROM diary_fts WHERE diary_fts MATCH ?",
        ("hello",),
    ).fetchall()
    assert any(h[0] == eid for h in hits)
    conn.close()


def test_see_also_rejects_self(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "diary.db"))
    conn = connect()
    eid = conn.execute("INSERT INTO entries(body) VALUES ('x')").lastrowid
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO see_also(entry_id, related_entry_id) VALUES (?,?)",
            (eid, eid),
        )
        conn.commit()
    conn.close()


def test_connect_explicit_path(tmp_path):
    db = tmp_path / "explicit.db"
    conn = connect(db)
    assert db.exists()
    conn.close()


def test_vec_hooks_unavailable(monkeypatch):
    monkeypatch.setattr(vec_hooks, "sqlite_vec_available", lambda: False)
    conn = sqlite3.connect(":memory:")
    assert vec_hooks.try_load_sqlite_vec(conn) is False
    assert vec_hooks.ensure_vec0(conn) is None
    conn.close()


def test_try_load_catches_attribute_error(monkeypatch):
    monkeypatch.setattr(vec_hooks, "sqlite_vec_available", lambda: True)

    class FakeVec:
        @staticmethod
        def load(conn):
            raise AssertionError("should not be called if enable fails first")

    import sys

    monkeypatch.setitem(sys.modules, "sqlite_vec", FakeVec)

    class Conn:
        def enable_load_extension(self, _enabled):
            raise AttributeError("no extensions")

    assert vec_hooks.try_load_sqlite_vec(Conn()) is False  # type: ignore[arg-type]


def test_ensure_vec0_when_load_ok(monkeypatch):
    monkeypatch.setattr(vec_hooks, "try_load_sqlite_vec", lambda _c: True)

    class FakeConn:
        def __init__(self):
            self._exists = False
            self.committed = False

        def execute(self, sql, parameters=()):
            if "sqlite_master" in sql:
                return [(1,)] if self._exists else []
            if "USING vec0" in sql or "CREATE VIRTUAL TABLE" in sql:
                self._exists = True
                return []
            return []

        def commit(self):
            self.committed = True

        def fetchone(self):
            return None

    # Row-like: execute().fetchone()
    class Cursor:
        def __init__(self, rows):
            self._rows = rows

        def fetchone(self):
            return self._rows[0] if self._rows else None

    class FakeConn2:
        def __init__(self):
            self._exists = False
            self.committed = False

        def execute(self, sql, parameters=()):
            if "sqlite_master" in sql:
                return Cursor([(1,)] if self._exists else [])
            if "vec0" in sql:
                self._exists = True
                return Cursor([])
            return Cursor([])

        def commit(self):
            self.committed = True

    conn = FakeConn2()
    assert vec_hooks.ensure_vec0(conn, dimensions=8) == "diary_summary_vec"  # type: ignore[arg-type]
    assert conn.committed is True
    assert vec_hooks.ensure_vec0(conn, dimensions=8) == "diary_summary_vec"  # type: ignore[arg-type]


def test_sqlite_vec_available_import_paths(monkeypatch):
    import builtins
    import sys

    real_import = builtins.__import__

    def boom(name, *a, **k):
        if name == "sqlite_vec":
            raise ImportError("nope")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", boom)
    assert vec_hooks.sqlite_vec_available() is False

    def ok(name, *a, **k):
        if name == "sqlite_vec":
            return type(sys)("sqlite_vec")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", ok)
    assert vec_hooks.sqlite_vec_available() is True
