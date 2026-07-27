"""Document search tool wrapping hybrid RAG + citations."""

from __future__ import annotations

from typing import Any

from geoagent.rag.chunkers import structural_chunk
from geoagent.rag.citations import citation_from_chunk
from geoagent.rag.hybrid_retriever import InMemoryHybridRetriever
from geoagent.rag.ingest import DEFAULT_CORPUS_DIR
from geoagent.rag.postgres_retriever import PostgresHybridRetriever
from geoagent.rag.reranker import rerank


def _fixture_retriever() -> InMemoryHybridRetriever:
    chunks = []
    for path in sorted(DEFAULT_CORPUS_DIR.glob("*.md")):
        chunks.extend(structural_chunk(path.stem, path.read_text(encoding="utf-8")))
    return InMemoryHybridRetriever(chunks)


def docs_search(
    query: str,
    *,
    top_k: int = 5,
    prefer_postgres: bool = True,
) -> dict[str, Any]:
    """Hybrid document retrieval with span/quote citations."""
    hits = []
    backend = "fixture-memory"
    if prefer_postgres:
        try:
            retriever = PostgresHybridRetriever()
            hits = retriever.search(query, top_k=top_k, mode="hybrid", use_rerank=True)
            backend = "postgres-hybrid"
        except Exception:
            hits = []
    if not hits:
        mem = _fixture_retriever()
        hits = rerank(query, mem.search(query, top_k=top_k * 2, mode="hybrid"), top_k=top_k)
        backend = "fixture-memory"

    evidence = []
    for hit in hits:
        cite = citation_from_chunk(hit.chunk)
        evidence.append(
            {
                "score": hit.score,
                "source": hit.source,
                "citation": cite.model_dump(),
                "text": hit.chunk.text,
            }
        )
    return {"ok": True, "backend": backend, "query": query, "evidence": evidence}
