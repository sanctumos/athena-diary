"""Tests for diary_write / diary_get."""

import pytest

from athena_diary_mcp.db import connect
from athena_diary_mcp.store import (
    DiaryError,
    add_see_also,
    entry_detail,
    ensure_lesson_family,
    get_entry,
    list_unprocessed,
    set_entry_tags,
    write_entry,
)


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


def test_entry_detail_includes_cross_refs(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    a = write_entry(conn, "first take on the pattern")
    b = write_entry(conn, "revisiting the pattern later")
    add_see_also(conn, a.id, b.id)
    set_entry_tags(conn, b.id, ["pattern", "revision"])
    lf_id = ensure_lesson_family(conn, "self-observation")
    conn.execute(
        "UPDATE entries SET lesson_family_id = ? WHERE id = ?",
        (lf_id, b.id),
    )
    conn.commit()
    detail = entry_detail(conn, get_entry(conn, b.id))
    assert detail["see_also_entry_ids"] == [a.id]
    assert detail["see_also_older_entry_ids"] == [a.id]
    assert detail["see_also_newer_entry_ids"] == []
    detail_a = entry_detail(conn, get_entry(conn, a.id))
    assert detail_a["see_also_newer_entry_ids"] == [b.id]
    assert detail_a["see_also_older_entry_ids"] == []
    assert detail["tags"] == ["pattern", "revision"]
    assert detail["lesson_family_slug"] == "self-observation"
    conn.close()
