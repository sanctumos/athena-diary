"""Tests for diary_write / diary_get."""

import pytest

from athena_diary_mcp.db import connect
from athena_diary_mcp.store import DiaryError, get_entry, list_unprocessed, write_entry


def test_write_and_get(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    e = write_entry(conn, "  noticed something  ", summary="notice", run_id="run-1")
    assert e.id > 0
    assert e.body == "noticed something"
    assert e.summary == "notice"
    assert e.source == "hot_turn"
    assert e.run_id == "run-1"
    got = get_entry(conn, e.id)
    assert got.body == e.body
    conn.close()


def test_write_rejects_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    with pytest.raises(DiaryError):
        write_entry(conn, "   ")
    with pytest.raises(DiaryError):
        write_entry(conn, "")
    conn.close()


def test_get_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    with pytest.raises(DiaryError, match="not found"):
        get_entry(conn, 99999)
    conn.close()


def test_list_unprocessed(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    a = write_entry(conn, "one")
    b = write_entry(conn, "two")
    conn.execute(
        "UPDATE entries SET sleeptime_processed_at = datetime('now') WHERE id = ?",
        (a.id,),
    )
    conn.commit()
    pending = list_unprocessed(conn, limit=10)
    assert [e.id for e in pending] == [b.id]
    conn.close()
