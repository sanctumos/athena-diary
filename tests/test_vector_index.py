"""Tests for vector store + semantic diary_search (#2430)."""

from athena_diary_mcp.db import connect
from athena_diary_mcp.embeddings import EmbedProvider, EmbedResult, HashEmbedProvider
from athena_diary_mcp.search import SearchHit, search_diary
from athena_diary_mcp.store import write_entry
from athena_diary_mcp.vector_index import (
    cosine,
    embed_and_store,
    pack_vector,
    search_similar,
    unpack_vector,
)


class FixedEmbedProvider(EmbedProvider):
    """Map substrings to fixed unit vectors for deterministic KNN tests."""

    def __init__(self):
        self.provider = "fixed"
        self.model = "fixed-v1"
        self._map = {
            "venice": (1.0, 0.0, 0.0, 0.0),
            "shop": (0.0, 1.0, 0.0, 0.0),
            "other": (0.0, 0.0, 1.0, 0.0),
        }

    def _vec_for(self, text: str) -> tuple[float, ...]:
        t = (text or "").lower()
        for key, vec in self._map.items():
            if key in t:
                return vec
        return (0.0, 0.0, 0.0, 1.0)

    def embed(self, texts):
        out = []
        for t in texts:
            v = self._vec_for(t)
            out.append(
                EmbedResult(
                    vector=v, model=self.model, provider=self.provider, dim=len(v)
                )
            )
        return out


def test_pack_unpack_roundtrip():
    v = (0.1, -0.2, 0.3)
    got = unpack_vector(pack_vector(v))
    assert len(got) == 3
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, v))


def test_cosine_identical():
    v = (1.0, 0.0, 0.0)
    assert abs(cosine(v, v) - 1.0) < 1e-6
    assert cosine((), (1.0,)) == -1.0


def test_embed_store_and_similar(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    prov = FixedEmbedProvider()
    a = write_entry(
        conn, "long body about Venice billing", summary="Venice billing prefs"
    )
    b = write_entry(conn, "groceries milk eggs", summary="shopping list")
    embed_and_store(conn, a.id, a.summary or "", provider=prov)
    embed_and_store(conn, b.id, b.summary or "", provider=prov)

    hits = search_similar(
        conn, "Venice billing", limit=5, provider=prov, min_score=0.0
    )
    assert hits
    assert hits[0].id == a.id
    assert hits[0].rank == "vec"
    conn.close()


def test_search_diary_prefers_vec_then_fts(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    prov = FixedEmbedProvider()
    fts_only = write_entry(
        conn, "uniquekeyword zebra alphabet", summary="fts only row"
    )
    sem = write_entry(conn, "body", summary="Venice inference preference")
    embed_and_store(conn, sem.id, sem.summary or "", provider=prov)

    hits = search_diary(conn, "uniquekeyword", limit=10, provider=prov)
    ids = [h.id for h in hits]
    assert fts_only.id in ids

    hits2 = search_diary(conn, "Venice inference", limit=10, provider=prov)
    assert any(h.id == sem.id for h in hits2)
    assert hits2[0].rank == "vec" or hits2[0].id == sem.id
    conn.close()


def test_search_diary_empty_query(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    assert search_diary(conn, "  ") == []
    conn.close()


def test_hash_provider_still_stores(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    e = write_entry(conn, "x", summary="y")
    r = embed_and_store(conn, e.id, "y", provider=HashEmbedProvider(dim=8))
    assert r.dim == 8
    row = conn.execute(
        "SELECT dim, provider FROM embeddings WHERE entry_id=?", (e.id,)
    ).fetchone()
    assert int(row["dim"]) == 8
    assert row["provider"] == "hash"
    conn.close()


def test_store_embedding_vec0_path_mocked(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    e = write_entry(conn, "body", summary="venice")
    prov = FixedEmbedProvider()
    result = prov.embed(["venice"])[0]

    calls = {"n": 0}

    def fake_ensure(c, dimensions=8):
        calls["n"] += 1
        # Simulate vec0 present but INSERT fails → BLOB still wins
        c.execute(
            "CREATE TABLE IF NOT EXISTS diary_summary_vec "
            "(entry_id INTEGER PRIMARY KEY, embedding TEXT)"
        )
        return "diary_summary_vec"

    monkeypatch.setattr(
        "athena_diary_mcp.vector_index.ensure_vec0", fake_ensure
    )
    from athena_diary_mcp.vector_index import store_embedding

    store_embedding(conn, e.id, result)
    assert calls["n"] >= 1
    row = conn.execute(
        "SELECT entry_id FROM embeddings WHERE entry_id=?", (e.id,)
    ).fetchone()
    assert row is not None
    conn.close()


def test_search_similar_vec0_knn_success(monkeypatch):
    """Exercise vec0 MATCH success path without real sqlite-vec."""
    from unittest.mock import MagicMock

    from athena_diary_mcp import vector_index as vi

    monkeypatch.setattr(vi, "ensure_vec0", lambda conn, dimensions=8: "diary_summary_vec")

    row = {"entry_id": 7}
    conn = MagicMock()
    # first execute = MATCH query
    conn.execute.return_value.fetchall.return_value = [row]

    def fake_hits(c, ids, *, rank):
        return [
            SearchHit(
                id=7,
                summary="s",
                created_at="t",
                source="hot_turn",
                rank=rank,
            )
        ]

    monkeypatch.setattr(vi, "_hits_from_ids", fake_hits)
    hits = vi.search_similar(conn, "venice", limit=5, provider=FixedEmbedProvider())
    assert hits and hits[0].id == 7 and hits[0].rank == "vec"


def test_search_similar_vec0_knn_falls_back(monkeypatch, tmp_path):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    e = write_entry(conn, "body", summary="venice")
    prov = FixedEmbedProvider()
    embed_and_store(conn, e.id, "venice", provider=prov)

    from athena_diary_mcp import vector_index as vi

    def boom_ensure(c, dimensions=8):
        return "diary_summary_vec"

    monkeypatch.setattr(vi, "ensure_vec0", boom_ensure)

    # Real conn: MATCH on nonexistent table raises → BLOB fallback
    hits = search_similar(conn, "venice", limit=5, provider=prov, min_score=0.0)
    assert any(h.id == e.id for h in hits)
    conn.close()


def test_dim_mismatch_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("DIARY_DB", str(tmp_path / "d.db"))
    conn = connect()
    e = write_entry(conn, "b", summary="venice")
    # Store 2-dim vector manually
    from athena_diary_mcp.vector_index import pack_vector

    conn.execute(
        "INSERT INTO embeddings(entry_id, model, provider, dim, vector) VALUES (?,?,?,?,?)",
        (e.id, "m", "t", 2, pack_vector((1.0, 0.0))),
    )
    conn.commit()
    # Query with 4-dim FixedEmbedProvider → dim mismatch skipped
    hits = search_similar(
        conn, "venice", limit=5, provider=FixedEmbedProvider(), min_score=0.0
    )
    assert hits == []
    conn.close()
