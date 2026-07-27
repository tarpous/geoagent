"""Citation packet helpers for librarian outputs."""

from __future__ import annotations

from geoagent.rag.chunkers import Chunk
from geoagent.schemas import Citation


def citation_from_chunk(chunk: Chunk, *, quote_max: int = 300) -> Citation:
    quote = chunk.text.strip()
    if len(quote) > quote_max:
        quote = quote[: quote_max - 1] + "…"
    return Citation(
        doc_id=chunk.doc_id,
        chunk_id=chunk.chunk_id,
        span_start=chunk.span_start,
        span_end=chunk.span_end,
        quote=quote,
    )
