"""RAG package exports."""

from geoagent.rag.chunkers import Chunk, fixed_size_chunk, structural_chunk
from geoagent.rag.citations import citation_from_chunk
from geoagent.rag.embeddings import EMBED_DIM, embed_text
from geoagent.rag.hybrid_retriever import (
    InMemoryHybridRetriever,
    ScoredChunk,
    reciprocal_rank_fusion,
)
from geoagent.rag.ingest import ingest_corpus
from geoagent.rag.postgres_retriever import PostgresHybridRetriever
from geoagent.rag.reranker import rerank

__all__ = [
    "EMBED_DIM",
    "Chunk",
    "InMemoryHybridRetriever",
    "PostgresHybridRetriever",
    "ScoredChunk",
    "citation_from_chunk",
    "embed_text",
    "fixed_size_chunk",
    "ingest_corpus",
    "reciprocal_rank_fusion",
    "rerank",
    "structural_chunk",
]
