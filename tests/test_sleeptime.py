"""Tests for diary_sleeptime_pass clerk (#2431)."""

from athena_diary_mcp.db import connect
from athena_diary_mcp.embeddings import HashEmbedProvider
from athena_diary_mcp.sleeptime import (
    DEFAULT_SEE_ALSO_MIN_SCORE,
    default_annotator,
    explicit_entry_refs,
    see_also_relink_pass,
    sleeptime_pass,
)
from athena_diary_mcp.store import Entry, get_entry, list_see_also, list_unprocessed, write_entry


def test_default_annotator_extracts_tags():
    e = Entry(
        id=1,
        body="Venice billing preference noted during ops review",
        summary=None,
        sensitivity_note=None,
        source="hot_turn",
        created_at="t",
        updated_at="t",
    )
    gist, tags, lesson = default_annotator(e)
    assert "Venice" in gist or "venice" in gist.lower()
    assert "venice" in tags
    assert lesson == tags[0]


def test_sleeptime_batch_limit_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    monkeypatch.setenv("DIARY_EMBED_MODE", "hash")
    conn = connect()
    prov = HashEmbedProvider(dim=8)
    # backlog > N
    ids = []
    for i in range(5):
        e = write_entry(conn, f"entry number {i} about sleeptime clerk work")
        ids.append(e.id)

    r1 = sleeptime_pass(conn, limit=2, provider=prov)
    assert r1.processed == 2
    assert len(r1.entry_ids) == 2
    pending = list_unprocessed(conn, limit=50)
    assert len(pending) == 3

    # First two stamped
    for eid in r1.entry_ids:
        e = get_entry(conn, eid)
        assert e.sleeptime_processed_at is not None
        assert e.summary and "GIST:" in e.summary
        assert e.lesson_family_id is not None

    # Second pass continues; re-running does not reselect done
    r2 = sleeptime_pass(conn, limit=2, provider=prov)
    assert r2.processed == 2
    assert set(r2.entry_ids).isdisjoint(set(r1.entry_ids))

    r3 = sleeptime_pass(conn, limit=10, provider=prov)
    assert r3.processed == 1
    assert list_unprocessed(conn, limit=50) == []

    # Idempotent empty pass
    r4 = sleeptime_pass(conn, limit=5, provider=prov)
    assert r4.processed == 0
    conn.close()


def test_sleeptime_see_also_dedupe(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()

    # Identical bodies → same hash embed after clerk → see_also link
    a = write_entry(conn, "exact same diary note for cluster test alpha")
    b = write_entry(conn, "exact same diary note for cluster test alpha")
    from athena_diary_mcp.embeddings import HashEmbedProvider

    prov = HashEmbedProvider(dim=8)
    sleeptime_pass(conn, limit=10, provider=prov, dedupe_min_score=0.99)
    related = list_see_also(conn, a.id)
    assert b.id in related
    assert a.id in list_see_also(conn, b.id)
    conn.close()


def test_custom_annotator(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    e = write_entry(conn, "raw body ignored by custom annotator")

    def ann(entry):
        return "custom gist", ["alpha", "beta"], "custom-family"

    from athena_diary_mcp.embeddings import HashEmbedProvider

    sleeptime_pass(conn, limit=1, provider=HashEmbedProvider(dim=8), annotator=ann)
    got = get_entry(conn, e.id)
    assert "custom gist" in (got.summary or "")
    assert "LESSON_FAMILY: custom-family" in (got.summary or "")
    conn.close()


def test_explicit_entry_refs():
    assert explicit_entry_refs("correction to entry 35 about dogears") == (35,)
    assert explicit_entry_refs("see also #42 and entry 43") == (42, 43)
    assert explicit_entry_refs("revisits entry 7") == (7,)
    assert explicit_entry_refs("no refs here") == ()


def test_see_also_relink_pass_wires_processed(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    a = write_entry(conn, "exact same diary note for cluster test alpha")
    b = write_entry(conn, "exact same diary note for cluster test alpha")
    prov = HashEmbedProvider(dim=8)
    sleeptime_pass(conn, limit=10, provider=prov, dedupe_min_score=0.99)
    # Simulate stale clerk: remove links but keep processed stamp
    conn.execute("DELETE FROM see_also")
    conn.commit()
    assert list_see_also(conn, a.id) == []

    relink = see_also_relink_pass(
        conn, limit=10, provider=prov, min_score=DEFAULT_SEE_ALSO_MIN_SCORE
    )
    assert relink.scanned >= 2
    assert b.id in list_see_also(conn, a.id)
    conn.close()


def test_see_also_relink_explicit_body_ref(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    prov = HashEmbedProvider(dim=8)
    original = write_entry(conn, "canonical note about boundary patterns")
    sleeptime_pass(conn, limit=5, provider=prov)
    followup = write_entry(
        conn, f"correction to entry {original.id}: refined boundary view"
    )
    sleeptime_pass(conn, limit=5, provider=prov)
    conn.execute("DELETE FROM see_also")
    conn.commit()

    see_also_relink_pass(conn, limit=10, provider=prov, min_score=0.99)
    assert followup.id in list_see_also(conn, original.id)
    assert original.id in list_see_also(conn, followup.id)
    conn.close()
