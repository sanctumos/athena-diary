# SPDX-License-Identifier: AGPL-3.0-only
"""Embed provider abstraction — letta (default) | external | deterministic test."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence


class EmbedError(RuntimeError):
    """Embedding provider failure."""


@dataclass(frozen=True)
class EmbedResult:
    vector: tuple[float, ...]
    model: str
    provider: str
    dim: int


class EmbedProvider(ABC):
    @abstractmethod
    def embed(self, texts: Sequence[str]) -> List[EmbedResult]:
        """Embed one or more texts; len(results) == len(texts)."""


def _pack_hash_vector(text: str, dim: int) -> tuple[float, ...]:
    """Deterministic pseudo-embedding from text hash (tests / offline)."""
    out: list[float] = []
    seed = text.encode("utf-8")
    i = 0
    while len(out) < dim:
        digest = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for j in range(0, len(digest) - 3, 4):
            if len(out) >= dim:
                break
            # Map u32 -> [-1, 1]
            (u,) = struct.unpack_from(">I", digest, j)
            out.append((u / 0xFFFFFFFF) * 2.0 - 1.0)
        i += 1
    # L2 normalize
    norm = sum(x * x for x in out) ** 0.5 or 1.0
    return tuple(x / norm for x in out)


class HashEmbedProvider(EmbedProvider):
    """Offline deterministic embedder for unit tests (no network)."""

    def __init__(self, dim: int = 8, model: str = "hash-v1"):
        self.dim = dim
        self.model = model
        self.provider = "hash"

    def embed(self, texts: Sequence[str]) -> List[EmbedResult]:
        return [
            EmbedResult(
                vector=_pack_hash_vector(t or "", self.dim),
                model=self.model,
                provider=self.provider,
                dim=self.dim,
            )
            for t in texts
        ]


class ExternalEmbedProvider(EmbedProvider):
    """OpenAI-compatible /embeddings POST (DIARY_EMBED_*)."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout: float = 30.0,
        opener: Optional[Callable[..., object]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self._opener = opener or urllib.request.urlopen
        self.provider = "external"

    def embed(self, texts: Sequence[str]) -> List[EmbedResult]:
        if not texts:
            return []
        url = f"{self.base_url}/embeddings"
        payload = json.dumps({"model": self.model, "input": list(texts)}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with self._opener(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.URLError as e:
            raise EmbedError(f"external embed failed: {e}") from e
        try:
            data = json.loads(raw.decode("utf-8"))
            items = sorted(data["data"], key=lambda x: int(x["index"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
            raise EmbedError(f"bad embed response: {e}") from e
        out: List[EmbedResult] = []
        for item in items:
            vec = tuple(float(x) for x in item["embedding"])
            out.append(
                EmbedResult(
                    vector=vec,
                    model=self.model,
                    provider=self.provider,
                    dim=len(vec),
                )
            )
        if len(out) != len(texts):
            raise EmbedError(
                f"embed count mismatch: got {len(out)} for {len(texts)} texts"
            )
        return out


class LettaEmbedProvider(EmbedProvider):
    """
    Sanctum/Letta shared embed lane.

    Uses DIARY_LETTA_EMBED_URL (+ optional key) when set; otherwise falls back to
    HashEmbedProvider so local/dev installs do not require a live Letta embed endpoint.
    Production moya should set DIARY_LETTA_EMBED_URL to the instance embed proxy.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        dim: int = 8,
        opener: Optional[Callable[..., object]] = None,
    ):
        self.base_url = (base_url or os.environ.get("DIARY_LETTA_EMBED_URL") or "").rstrip(
            "/"
        )
        self.model = model or os.environ.get("DIARY_LETTA_EMBED_MODEL") or "letta-default"
        self.api_key = api_key if api_key is not None else os.environ.get(
            "DIARY_LETTA_EMBED_API_KEY", ""
        )
        self.dim = dim
        self.provider = "letta"
        self._opener = opener
        self._fallback = HashEmbedProvider(dim=dim, model=f"letta-hash:{self.model}")

    def embed(self, texts: Sequence[str]) -> List[EmbedResult]:
        if not self.base_url:
            results = self._fallback.embed(texts)
            return [
                EmbedResult(
                    vector=r.vector,
                    model=self.model,
                    provider="letta",
                    dim=r.dim,
                )
                for r in results
            ]
        ext = ExternalEmbedProvider(
            base_url=self.base_url,
            model=self.model,
            api_key=self.api_key or "unused",
            opener=self._opener,
        )
        results = ext.embed(texts)
        return [
            EmbedResult(
                vector=r.vector,
                model=r.model,
                provider="letta",
                dim=r.dim,
            )
            for r in results
        ]


def get_embed_provider(
    mode: Optional[str] = None,
    *,
    opener: Optional[Callable[..., object]] = None,
) -> EmbedProvider:
    """
    Factory from DIARY_EMBED_MODE.

    Modes: letta (default), external, hash (explicit offline).
    """
    m = (mode or os.environ.get("DIARY_EMBED_MODE") or "letta").strip().lower()
    if m == "hash":
        dim = int(os.environ.get("DIARY_EMBED_DIM", "8"))
        return HashEmbedProvider(dim=dim)
    if m == "external":
        base = os.environ.get("DIARY_EMBED_BASE_URL") or ""
        model = os.environ.get("DIARY_EMBED_MODEL") or ""
        key = os.environ.get("DIARY_EMBED_API_KEY") or ""
        if not base or not model or not key:
            raise EmbedError(
                "external mode requires DIARY_EMBED_BASE_URL, DIARY_EMBED_MODEL, DIARY_EMBED_API_KEY"
            )
        return ExternalEmbedProvider(
            base_url=base, model=model, api_key=key, opener=opener
        )
    if m == "letta":
        return LettaEmbedProvider(opener=opener)
    raise EmbedError(f"unknown DIARY_EMBED_MODE: {m}")
