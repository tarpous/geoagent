"""Postgres hybrid retrieval tests (skipped when DB is unavailable)."""

from __future__ import annotations

import os

import pytest

from geoagent.rag import PostgresHybridRetriever, ingest_corpus

DSN = os.environ.get(
    "GEOAGENT_DATABASE_URL",
    "postgresql://geoagent:geoagent@127.0.0.1:5432/geoagent",
)


def _db_available() -> bool:
    try:
        import psycopg
        from pgvector.psycopg import register_vector

        with psycopg.connect(DSN, connect_timeout=2) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Postgres not available")


def test_postgres_ingest_and_hybrid_beats_dense():
    stats = ingest_corpus(dsn=DSN)
    assert stats["documents"] >= 2
    assert stats["chunks"] >= 2

    retriever = PostgresHybridRetriever(dsn=DSN)
    queries = [
        "tree cover loss near ring road",
        "flood-prone agricultural land",
        "Thessaloniki flood-risk farmland",
    ]

    def hit_rate(mode: str, use_rerank: bool) -> float:
        hits_ok = 0
        for q in queries:
            hits = retriever.search(q, top_k=5, mode=mode, use_rerank=use_rerank)
            blob = " ".join(h.chunk.text.lower() for h in hits)
            if any(tok in blob for tok in q.lower().split()[:2]):
                hits_ok += 1
        return hits_ok / len(queries)

    dense = hit_rate("dense", use_rerank=False)
    hybrid = hit_rate("hybrid", use_rerank=True)
    assert hybrid >= dense
