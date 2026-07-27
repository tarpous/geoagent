"""Offline retrieval metrics over fixture corpus."""

from __future__ import annotations

from pathlib import Path

from geoagent.rag import (
    InMemoryHybridRetriever,
    fixed_size_chunk,
    rerank,
    structural_chunk,
)

CORPUS = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "corpus"

# query -> relevant chunk text needles
CASES: list[tuple[str, list[str]]] = [
    ("tree cover loss near ring road", ["tree cover loss", "ring road"]),
    ("flood-prone agricultural land Attica", ["flood-prone agricultural"]),
    ("Thessaloniki flood-risk farmland", ["flood-risk", "farmland"]),
    ("retention basins vegetation buffers", ["retention basins"]),
    ("early-warning systems Thessaloniki", ["early-warning"]),
]


def _load_chunks():
    chunks = []
    for path in sorted(CORPUS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        doc_id = path.stem
        chunks.extend(structural_chunk(doc_id, text))
        if len(chunks) < 3:
            chunks.extend(fixed_size_chunk(doc_id, text, size=220, overlap=40))
    return chunks


def recall_at_k(relevant_needles: list[str], hit_texts: list[str], k: int) -> float:
    top = hit_texts[:k]
    for needle in relevant_needles:
        if any(needle.lower() in text.lower() for text in top):
            return 1.0
    return 0.0


def evaluate(mode: str, *, use_rerank: bool) -> float:
    retriever = InMemoryHybridRetriever(_load_chunks())
    scores: list[float] = []
    for query, needles in CASES:
        hits = retriever.search(query, top_k=8, mode=mode)
        if use_rerank:
            hits = rerank(query, hits, top_k=5)
        texts = [h.chunk.text for h in hits]
        scores.append(recall_at_k(needles, texts, 5))
    return sum(scores) / len(scores)


def test_hybrid_rerank_beats_dense_only_recall_at_5():
    dense = evaluate("dense", use_rerank=False)
    hybrid = evaluate("hybrid", use_rerank=True)
    assert hybrid >= dense
    assert hybrid > dense or hybrid == 1.0
    # Publish a minimal table for REPORT scaffolding.
    table = {
        "dense_recall@5": round(dense, 3),
        "hybrid_rerank_recall@5": round(hybrid, 3),
    }
    assert table["hybrid_rerank_recall@5"] >= table["dense_recall@5"]
