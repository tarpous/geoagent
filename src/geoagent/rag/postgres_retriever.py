"""Postgres hybrid retriever: FTS + pgvector + reciprocal-rank fusion."""

from __future__ import annotations

from dataclasses import dataclass

from geoagent.db import connect
from geoagent.rag.chunkers import Chunk
from geoagent.rag.embeddings import embed_text
from geoagent.rag.hybrid_retriever import ScoredChunk, reciprocal_rank_fusion
from geoagent.rag.reranker import rerank


@dataclass(slots=True)
class PostgresHybridRetriever:
    dsn: str | None = None
    candidate_k: int = 20

    def _fetch_fts(self, query: str, limit: int) -> list[tuple[str, float]]:
        sql = """
            SELECT chunk_id, ts_rank_cd(tsv, plainto_tsquery('english', %s)) AS score
            FROM chunks
            WHERE tsv @@ plainto_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT %s
        """
        with connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (query, query, limit))
            return [(row[0], float(row[1])) for row in cur.fetchall()]

    def _fetch_dense(self, query: str, limit: int) -> list[tuple[str, float]]:
        embedding = embed_text(query)
        sql = """
            SELECT chunk_id, 1 - (embedding <=> %s) AS score
            FROM chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        with connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (embedding, embedding, limit))
            return [(row[0], float(row[1])) for row in cur.fetchall()]

    def _load_chunks(self, chunk_ids: list[str]) -> dict[str, Chunk]:
        if not chunk_ids:
            return {}
        sql = """
            SELECT chunk_id, doc_id, text, span_start, span_end, heading
            FROM chunks
            WHERE chunk_id = ANY(%s)
        """
        with connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (chunk_ids,))
            out: dict[str, Chunk] = {}
            for chunk_id, doc_id, text, span_start, span_end, heading in cur.fetchall():
                out[chunk_id] = Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    text=text,
                    span_start=span_start,
                    span_end=span_end,
                    heading=heading,
                )
            return out

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        mode: str = "hybrid",
        use_rerank: bool = True,
    ) -> list[ScoredChunk]:
        fts = self._fetch_fts(query, self.candidate_k)
        dense = self._fetch_dense(query, self.candidate_k)
        if mode == "dense":
            ranked = dense
            source = "dense"
        elif mode == "lexical":
            ranked = fts
            source = "lexical"
        else:
            ranked = reciprocal_rank_fusion(
                [[cid for cid, _ in fts], [cid for cid, _ in dense]]
            )
            source = "hybrid"

        chunk_ids = [cid for cid, _ in ranked[: max(top_k * 2, top_k)]]
        loaded = self._load_chunks(chunk_ids)
        hits: list[ScoredChunk] = []
        for chunk_id, score in ranked:
            chunk = loaded.get(chunk_id)
            if chunk is None:
                continue
            hits.append(ScoredChunk(chunk=chunk, score=score, source=source))
            if len(hits) >= top_k * 2:
                break
        if use_rerank:
            hits = rerank(query, hits, top_k=top_k)
        return hits[:top_k]
