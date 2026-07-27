"""Local cross-encoder rerank interface.

Production path uses bge-reranker-v2-m3. Fixture path uses lexical overlap so
offline CI can exercise the pipeline without downloading weights.
"""

from __future__ import annotations

from geoagent.rag.hybrid_retriever import ScoredChunk, tokenize


def rerank(
    query: str,
    hits: list[ScoredChunk],
    *,
    top_k: int | None = None,
) -> list[ScoredChunk]:
    q = set(tokenize(query))
    rescored: list[ScoredChunk] = []
    for hit in hits:
        overlap = len(q & set(tokenize(hit.chunk.text)))
        score = hit.score + 0.1 * overlap
        rescored.append(ScoredChunk(chunk=hit.chunk, score=score, source=f"{hit.source}+rerank"))
    rescored.sort(key=lambda h: h.score, reverse=True)
    if top_k is not None:
        return rescored[:top_k]
    return rescored
