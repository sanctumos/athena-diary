"""Tests for summary template + embed providers (#2429)."""

import io
import json
from urllib.error import URLError

import pytest

from athena_diary_mcp.embeddings import (
    EmbedError,
    ExternalEmbedProvider,
    HashEmbedProvider,
    LettaEmbedProvider,
    get_embed_provider,
)
from athena_diary_mcp.summary import coerce_summary, format_summary, parse_summary, SummarySlots


def test_format_and_parse_roundtrip():
    text = format_summary(
        SummarySlots(gist="noticed Venice preference", tags=("billing", "ops"), lesson_family="infra")
    )
    assert "GIST:" in text
    assert "TAGS: billing, ops" in text
    assert "LESSON_FAMILY: infra" in text
    slots = parse_summary(text)
    assert slots.gist == "noticed Venice preference"
    assert slots.tags == ("billing", "ops")
    assert slots.lesson_family == "infra"


def test_coerce_empty_slots():
    text = coerce_summary("", tags=[], lesson_family=None)
    assert "(empty)" in text
    assert "(none)" in text


def test_hash_embed_deterministic():
    p = HashEmbedProvider(dim=8)
    a = p.embed(["hello"])[0]
    b = p.embed(["hello"])[0]
    c = p.embed(["world"])[0]
    assert a.vector == b.vector
    assert a.vector != c.vector
    assert a.dim == 8
    assert a.provider == "hash"
    # unit-ish
    n = sum(x * x for x in a.vector) ** 0.5
    assert abs(n - 1.0) < 1e-6


def test_get_provider_modes(monkeypatch):
    monkeypatch.setenv("DIARY_EMBED_MODE", "hash")
    monkeypatch.setenv("DIARY_EMBED_DIM", "4")
    p = get_embed_provider()
    assert isinstance(p, HashEmbedProvider)
    assert p.embed(["x"])[0].dim == 4

    monkeypatch.setenv("DIARY_EMBED_MODE", "letta")
    monkeypatch.delenv("DIARY_LETTA_EMBED_URL", raising=False)
    p2 = get_embed_provider()
    assert isinstance(p2, LettaEmbedProvider)
    r = p2.embed(["offline"])[0]
    assert r.provider == "letta"

    monkeypatch.setenv("DIARY_EMBED_MODE", "nope")
    with pytest.raises(EmbedError, match="unknown"):
        get_embed_provider()


def test_external_requires_env(monkeypatch):
    monkeypatch.setenv("DIARY_EMBED_MODE", "external")
    monkeypatch.delenv("DIARY_EMBED_BASE_URL", raising=False)
    monkeypatch.delenv("DIARY_EMBED_MODEL", raising=False)
    monkeypatch.delenv("DIARY_EMBED_API_KEY", raising=False)
    with pytest.raises(EmbedError, match="requires"):
        get_embed_provider()


class _FakeResp:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_external_embed_mocked():
    def opener(req, timeout=30):
        return _FakeResp(
            {
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                ]
            }
        )

    p = ExternalEmbedProvider(
        base_url="https://example.test/v1",
        model="m1",
        api_key="k",
        opener=opener,
    )
    results = p.embed(["a", "b"])
    assert len(results) == 2
    assert results[0].vector == (0.1, 0.2, 0.3)
    assert results[0].provider == "external"


def test_external_embed_network_error():
    def opener(req, timeout=30):
        raise URLError("down")

    p = ExternalEmbedProvider(
        base_url="https://example.test/v1", model="m", api_key="k", opener=opener
    )
    with pytest.raises(EmbedError, match="failed"):
        p.embed(["x"])


def test_letta_with_url_mocked(monkeypatch):
    def opener(req, timeout=30):
        return _FakeResp({"data": [{"index": 0, "embedding": [1.0, 0.0]}]})

    p = LettaEmbedProvider(base_url="https://letta.test/v1", model="lm", opener=opener)
    r = p.embed(["z"])[0]
    assert r.provider == "letta"
    assert r.vector == (1.0, 0.0)
