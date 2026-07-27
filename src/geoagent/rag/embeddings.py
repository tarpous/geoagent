"""Deterministic offline embeddings for CI/fixtures.

Production path will call BGE-M3 via the Hugging Face stack. This hasher keeps
pgvector wiring and hybrid evals runnable without downloading model weights.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN = re.compile(r"[a-z0-9_]+", re.I)
EMBED_DIM = 384


def embed_text(text: str, *, dim: int = EMBED_DIM) -> list[float]:
    vec = [0.0] * dim
    tokens = [t.lower() for t in _TOKEN.findall(text)]
    if not tokens:
        return vec
    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
