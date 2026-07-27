"""Corpus ingest into Postgres (documents + chunk embeddings)."""

from __future__ import annotations

import csv
from pathlib import Path

from geoagent.db import connect
from geoagent.rag.chunkers import structural_chunk
from geoagent.rag.embeddings import embed_text

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = ROOT / "data" / "corpus_manifest.csv"
DEFAULT_CORPUS_DIR = ROOT / "data" / "fixtures" / "corpus"


def _load_body(doc_id: str, corpus_dir: Path) -> str:
    md = corpus_dir / f"{doc_id}.md"
    if md.is_file():
        return md.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No fixture body for doc_id={doc_id} under {corpus_dir}")


def ingest_corpus(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    dsn: str | None = None,
) -> dict[str, int]:
    from pgvector import Vector

    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    docs = 0
    chunks = 0
    with connect(dsn) as conn:
        with conn.cursor() as cur:
            for row in rows:
                doc_id = row["doc_id"]
                body = _load_body(doc_id, corpus_dir)
                cur.execute(
                    """
                    INSERT INTO documents (doc_id, title, source_url, license, retrieval_date, body)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        source_url = EXCLUDED.source_url,
                        license = EXCLUDED.license,
                        retrieval_date = EXCLUDED.retrieval_date,
                        body = EXCLUDED.body
                    """,
                    (
                        doc_id,
                        row["title"],
                        row.get("source_url"),
                        row["license"],
                        row.get("retrieval_date") or None,
                        body,
                    ),
                )
                docs += 1
                cur.execute("DELETE FROM chunks WHERE doc_id = %s", (doc_id,))
                for chunk in structural_chunk(doc_id, body):
                    embedding = Vector(embed_text(chunk.text))
                    cur.execute(
                        """
                        INSERT INTO chunks (
                            chunk_id, doc_id, text, span_start, span_end, heading, embedding
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            chunk.chunk_id,
                            chunk.doc_id,
                            chunk.text,
                            chunk.span_start,
                            chunk.span_end,
                            chunk.heading,
                            embedding,
                        ),
                    )
                    chunks += 1
        conn.commit()
    return {"documents": docs, "chunks": chunks}


def main() -> int:
    import json

    stats = ingest_corpus()
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
