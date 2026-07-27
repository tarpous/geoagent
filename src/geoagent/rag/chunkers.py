"""Document chunking strategies."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    span_start: int
    span_end: int
    heading: str | None = None


def fixed_size_chunk(
    doc_id: str,
    text: str,
    *,
    size: int = 400,
    overlap: int = 80,
) -> list[Chunk]:
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(len(text), start + size)
        piece = text[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}:fixed:{idx}",
                    doc_id=doc_id,
                    text=piece,
                    span_start=start,
                    span_end=end,
                )
            )
            idx += 1
        if end >= len(text):
            break
        start = end - overlap
    return chunks


_HEADING = re.compile(r"(?m)^(#{1,3}\s+.+)$")


def structural_chunk(doc_id: str, text: str, *, max_chars: int = 600) -> list[Chunk]:
    """Split on markdown-ish headings, then fall back to fixed windows inside sections."""
    matches = list(_HEADING.finditer(text))
    if not matches:
        return fixed_size_chunk(doc_id, text, size=max_chars, overlap=max(40, max_chars // 8))

    sections: list[tuple[str | None, int, int]] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = match.group(1).strip()
        sections.append((heading, start, end))

    if matches[0].start() > 0:
        sections.insert(0, (None, 0, matches[0].start()))

    chunks: list[Chunk] = []
    idx = 0
    for heading, start, end in sections:
        body = text[start:end].strip()
        if not body:
            continue
        if len(body) <= max_chars:
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}:struct:{idx}",
                    doc_id=doc_id,
                    text=body,
                    span_start=start,
                    span_end=end,
                    heading=heading,
                )
            )
            idx += 1
            continue
        for sub in fixed_size_chunk(doc_id, body, size=max_chars, overlap=max(40, max_chars // 8)):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}:struct:{idx}",
                    doc_id=doc_id,
                    text=sub.text,
                    span_start=start + sub.span_start,
                    span_end=start + sub.span_end,
                    heading=heading,
                )
            )
            idx += 1
    return chunks
