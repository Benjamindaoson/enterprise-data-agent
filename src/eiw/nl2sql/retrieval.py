"""Deterministic hybrid retrieval primitives for governed NL2SQL.

The production path can swap in OpenSearch/vector-model adapters later, but the
core contracts stay dependency-light and reproducible in CI.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    """A retrievable semantic/schema object."""

    object_id: str
    object_type: str
    text: str
    table_name: str | None = None
    column_name: str | None = None
    protected: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    """A ranked candidate with fusion provenance."""

    candidate: RetrievalCandidate
    score: float
    source_ranks: dict[str, int] = field(default_factory=dict)


class LexicalRetriever(Protocol):
    def retrieve(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        top_k: int,
    ) -> list[RetrievalHit]: ...


class DenseRetriever(Protocol):
    def retrieve(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        top_k: int,
    ) -> list[RetrievalHit]: ...


class Reranker(Protocol):
    def rerank(
        self,
        query: str,
        candidates: list[RetrievalHit],
        top_n: int,
    ) -> list[RetrievalHit]: ...


class InMemoryBM25Retriever:
    """Small deterministic BM25 implementation used by local/CI execution."""

    def __init__(self, *, k1: float = 1.2, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def retrieve(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        top_k: int,
    ) -> list[RetrievalHit]:
        if not candidates or top_k <= 0:
            return []

        docs = [_tokens(candidate.text) for candidate in candidates]
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        avg_len = sum(len(doc) for doc in docs) / max(len(docs), 1)
        avg_len = max(avg_len, 1.0)
        doc_freq: Counter[str] = Counter()
        for doc in docs:
            doc_freq.update(set(doc))

        total_docs = len(docs)
        scored: list[RetrievalHit] = []
        for candidate, doc in zip(candidates, docs, strict=True):
            counts = Counter(doc)
            score = 0.0
            for token in query_tokens:
                tf = counts[token]
                if not tf:
                    continue
                df = doc_freq[token]
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
                norm = tf + self.k1 * (
                    1.0 - self.b + self.b * len(doc) / avg_len
                )
                score += idf * (tf * (self.k1 + 1.0)) / max(norm, 1e-9)
            if score > 0:
                scored.append(RetrievalHit(candidate=candidate, score=score))

        scored.sort(key=lambda hit: (-hit.score, hit.candidate.object_id))
        return scored[:top_k]


class DeterministicDenseRetriever:
    """Dependency-free hashed token-vector retriever.

    This is deliberately a deterministic local provider, not a claim of neural
    semantic embeddings. A model-backed adapter can implement the same protocol.
    """

    def __init__(self, *, dimensions: int = 128) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be >= 8")
        self.dimensions = dimensions

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _tokens(text):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            raw = int.from_bytes(digest, "big")
            index = raw % self.dimensions
            sign = 1.0 if ((raw >> 8) & 1) == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def retrieve(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        top_k: int,
    ) -> list[RetrievalHit]:
        if not candidates or top_k <= 0:
            return []
        query_vector = self._vector(query)
        if not any(query_vector):
            return []

        scored: list[RetrievalHit] = []
        for candidate in candidates:
            vector = self._vector(candidate.text)
            score = sum(a * b for a, b in zip(query_vector, vector, strict=True))
            if score > 0:
                scored.append(RetrievalHit(candidate=candidate, score=score))
        scored.sort(key=lambda hit: (-hit.score, hit.candidate.object_id))
        return scored[:top_k]


def reciprocal_rank_fusion(
    rankings: dict[str, list[RetrievalHit]],
    *,
    k: int = 60,
    top_k: int | None = None,
) -> list[RetrievalHit]:
    """Fuse independent rankings without mixing incomparable raw scores."""

    if k <= 0:
        raise ValueError("RRF k must be > 0")

    candidates: dict[str, RetrievalCandidate] = {}
    scores: dict[str, float] = {}
    source_ranks: dict[str, dict[str, int]] = {}

    for source, hits in rankings.items():
        seen: set[str] = set()
        for rank, hit in enumerate(hits, start=1):
            object_id = hit.candidate.object_id
            if object_id in seen:
                continue
            seen.add(object_id)
            candidates[object_id] = hit.candidate
            scores[object_id] = scores.get(object_id, 0.0) + 1.0 / (k + rank)
            source_ranks.setdefault(object_id, {})[source] = rank

    fused = [
        RetrievalHit(
            candidate=candidates[object_id],
            score=score,
            source_ranks=source_ranks.get(object_id, {}),
        )
        for object_id, score in scores.items()
    ]
    fused.sort(key=lambda hit: (-hit.score, hit.candidate.object_id))
    return fused[:top_k] if top_k is not None else fused


class HeuristicReranker:
    """Deterministic reranker favoring explicit phrase/token evidence."""

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalHit],
        top_n: int,
    ) -> list[RetrievalHit]:
        query_lower = query.lower()
        query_tokens = set(_tokens(query))

        reranked: list[RetrievalHit] = []
        for hit in candidates:
            text_lower = hit.candidate.text.lower()
            candidate_tokens = set(_tokens(hit.candidate.text))
            overlap = len(query_tokens & candidate_tokens) / max(len(query_tokens), 1)
            phrase_bonus = 0.0
            for phrase in (
                hit.candidate.object_id.split(":", 1)[-1].replace("_", " "),
                hit.candidate.metadata.get("name", ""),
            ):
                phrase = phrase.strip().lower()
                if phrase and phrase in query_lower:
                    phrase_bonus = max(phrase_bonus, 1.0)
            protected_bonus = 0.25 if hit.candidate.protected else 0.0
            score = hit.score + overlap + phrase_bonus + protected_bonus
            reranked.append(
                RetrievalHit(
                    candidate=hit.candidate,
                    score=score,
                    source_ranks=hit.source_ranks,
                )
            )

        reranked.sort(key=lambda hit: (-hit.score, hit.candidate.object_id))
        return reranked[:top_n]


class HybridRetrievalService:
    """Single hybrid retrieval service used inside the governed NL2SQL path."""

    MODES = {"lexical_only", "dense_only", "hybrid", "hybrid_rerank"}

    def __init__(
        self,
        *,
        lexical: LexicalRetriever | None = None,
        dense: DenseRetriever | None = None,
        reranker: Reranker | None = None,
        rrf_k: int = 60,
    ) -> None:
        self.lexical = lexical or InMemoryBM25Retriever()
        self.dense = dense or DeterministicDenseRetriever()
        self.reranker = reranker or HeuristicReranker()
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        *,
        top_k: int = 8,
        mode: str = "hybrid_rerank",
    ) -> list[RetrievalHit]:
        if mode not in self.MODES:
            raise ValueError(f"unsupported retrieval mode: {mode}")
        if top_k <= 0:
            return []

        # Over-retrieve before fusion/reranking.
        pool_size = max(top_k * 3, top_k)
        lexical_hits = self.lexical.retrieve(query, candidates, pool_size)
        dense_hits = self.dense.retrieve(query, candidates, pool_size)

        if mode == "lexical_only":
            return lexical_hits[:top_k]
        if mode == "dense_only":
            return dense_hits[:top_k]

        fused = reciprocal_rank_fusion(
            {"lexical": lexical_hits, "dense": dense_hits},
            k=self.rrf_k,
            top_k=pool_size,
        )
        if mode == "hybrid":
            return fused[:top_k]
        return self.reranker.rerank(query, fused, top_k)
