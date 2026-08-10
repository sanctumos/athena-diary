"""Tests for FTS diary_search (#2428)."""

from athena_diary_mcp.db import connect
from athena_diary_mcp.search import sanitize_fts_query, search_diary, search_fts
from athena_diary_mcp.store import set_entry_tags, write_entry


def test_sanitize_strips_junk():
    assert sanitize_fts_query("hello, world!!!") == "hello world"
    assert sanitize_fts_query("   ") == ""
    assert sanitize_fts_query("") == ""


def test_search_fts_finds_body(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    a = write_entry(conn, "Mark prefers Venice for inference", summary="venice preference")
    write_entry(conn, "unrelated grocery list")
    hits = search_fts(conn, "Venice inference")
    assert [h.id for h in hits] == [a.id]
    assert hits[0].summary == "venice preference"
    assert hits[0].rank == "fts"
    # Default search does not return full bodies
    assert not hasattr(hits[0], "body") or getattr(hits[0], "body", None) is None
    conn.close()


def test_search_empty_query(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    write_entry(conn, "something")
    assert search_diary(conn, "!!!") == []
    assert search_diary(conn, "") == []
    conn.close()


def test_search_by_tag(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    e = write_entry(conn, "body without keyword", summary="quiet")
    set_entry_tags(conn, e.id, ["sleeptime", "billing"])
    hits = search_diary(conn, "billing")
    assert len(hits) == 1
    assert hits[0].id == e.id
    assert hits[0].rank == "tag"
    assert "billing" in hits[0].tags
    conn.close()
