"""Chunker unit tests."""

from geoagent.rag import citation_from_chunk, fixed_size_chunk, structural_chunk


def test_fixed_and_structural_chunkers():
    text = "# Title\n\nAlpha " * 50 + "\n## Section\n\nBeta ring road tree cover loss\n"
    fixed = fixed_size_chunk("doc", text, size=80, overlap=20)
    structural = structural_chunk("doc", text, max_chars=120)
    assert fixed
    assert structural
    assert structural[0].heading is not None or len(structural) >= 1
    cite = citation_from_chunk(structural[0])
    assert cite.doc_id == "doc"
    assert cite.quote
