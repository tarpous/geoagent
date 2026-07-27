"""Hybrid retrieval with reciprocal-rank fusion over fixture/in-memory indexes.

Postgres FTS + pgvector remain the production path (M1b once compose is available).
This module provides the algorithm and a fixture backend for offline evals.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass

from geoagent.rag.chunkers import Chunk

_TOKEN = re.compile(r"[a-z0-9_]+", re.I)


@dataclass(slots=True)
class ScoredChunk:
    chunk: Chunk
    score: float
    source: str


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


class InMemoryHybridRetriever:
    """Lexical + bag-of-words dense proxy with RRF fusion."""

    def __init__(self, chunks: list[Chunk]) -> None:
        if not chunks:
            raise ValueError("chunks must be non-empty")
        self.chunks = {c.chunk_id: c for c in chunks}
        self._df: dict[str, int] = defaultdict(int)
        self._tf: dict[str, dict[str, int]] = {}
        for chunk in chunks:
            tf: dict[str, int] = defaultdict(int)
            for tok in set(tokenize(chunk.text)):
                self._df[tok] += 1
            for tok in tokenize(chunk.text):
                tf[tok] += 1
            self._tf[chunk.chunk_id] = dict(tf)
        self._n_docs = len(chunks)

    def _lexical_scores(self, query: str) -> list[tuple[str, float]]:
        q_tokens = tokenize(query)
        scores: list[tuple[str, float]] = []
        for chunk_id, tf in self._tf.items():
            score = 0.0
            for tok in q_tokens:
                if tok not in tf:
                    continue
                idf = math.log((1 + self._n_docs) / (1 + self._df[tok])) + 1.0
                score += (1 + math.log(tf[tok])) * idf
            if score > 0:
                scores.append((chunk_id, score))
        scores.sort(key=lambda kv: kv[1], reverse=True)
        return scores

    def _dense_scores(self, query: str) -> list[tuple[str, float]]:
        # Offline proxy: cosine over binary term vectors (no embedding model required).
        q_set = set(tokenize(query))
        if not q_set:
            return []
        scores: list[tuple[str, float]] = []
        for chunk_id, tf in self._tf.items():
            terms = set(tf)
            if not terms:
                continue
            inter = len(q_set & terms)
            denom = math.sqrt(len(q_set) * len(terms))
            score = inter / denom if denom else 0.0
            if score > 0:
                scores.append((chunk_id, score))
        scores.sort(key=lambda kv: kv[1], reverse=True)
        return scores

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        mode: str = "hybrid",
    ) -> list[ScoredChunk]:
        lexical = self._lexical_scores(query)
        dense = self._dense_scores(query)
        if mode == "dense":
            ranked = dense
            source = "dense"
        elif mode == "lexical":
            ranked = lexical
            source = "lexical"
        else:
            fused = reciprocal_rank_fusion(
                [[cid for cid, _ in lexical], [cid for cid, _ in dense]]
            )
            ranked = fused
            source = "hybrid"
        out: list[ScoredChunk] = []
        for chunk_id, score in ranked[:top_k]:
            out.append(ScoredChunk(chunk=self.chunks[chunk_id], score=score, source=source))
        return out
