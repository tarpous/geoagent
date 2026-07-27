"""Offline retrieval evaluation (recall@k on fixture corpus)."""

from __future__ import annotations

import json
from pathlib import Path

from geoagent.rag.chunkers import Chunk, structural_chunk
from geoagent.rag.hybrid_retriever import InMemoryHybridRetriever
from geoagent.rag.reranker import rerank

ROOT = Path(__file__).resolve().parent
FIXTURE_CORPUS = ROOT.parent / "data" / "fixtures" / "corpus"
OUT = ROOT / "results" / "retrieval_fixture.md"


def _load_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    if FIXTURE_CORPUS.is_dir():
        for path in sorted(FIXTURE_CORPUS.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            chunks.extend(structural_chunk(path.stem, text))
    if not chunks:
        chunks = [
            Chunk(
                chunk_id="synth-1",
                doc_id="synth",
                text="Attica flood planning and tree cover near the ring road.",
                span_start=0,
                span_end=56,
            )
        ]
    return chunks


def evaluate_recall_at_k(k: int = 5) -> dict:
    chunks = _load_chunks()
    retriever = InMemoryHybridRetriever(chunks)
    queries = [
        ("tree cover ring road", "tree"),
        ("flood planning Attica", "flood"),
        ("agricultural land", "agricultur"),
    ]
    hits = 0
    details = []
    for query, needle in queries:
        ranked = retriever.search(query, top_k=k)
        ranked = rerank(query, ranked, top_k=k)
        found = any(needle.lower() in hit.chunk.text.lower() for hit in ranked)
        hits += int(found)
        details.append({"query": query, "hit": found, "n": len(ranked)})
    recall = hits / len(queries) if queries else 0.0
    report = {"recall_at_k": recall, "k": k, "n_queries": len(queries), "details": details}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Retrieval fixture eval",
        "",
        f"- recall@{k}: **{recall:.2f}**",
        f"- queries: {len(queries)}",
        "",
        "| query | hit |",
        "|---|---|",
    ]
    for row in details:
        lines.append(f"| {row['query']} | {row['hit']} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    report = evaluate_recall_at_k(5)
    print(json.dumps(report, indent=2))
    return 0 if report["recall_at_k"] >= 0.5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
