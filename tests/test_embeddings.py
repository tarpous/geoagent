"""Embedding helper tests."""

from geoagent.rag.embeddings import EMBED_DIM, embed_text


def test_embed_text_is_deterministic_and_normalized():
    a = embed_text("ring road tree cover")
    b = embed_text("ring road tree cover")
    assert a == b
    assert len(a) == EMBED_DIM
    norm = sum(v * v for v in a) ** 0.5
    assert abs(norm - 1.0) < 1e-6
