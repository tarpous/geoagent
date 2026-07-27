# Retrieval ablation (fixture / offline)

Measured on the committed markdown fixture corpus with the in-memory hybrid
retriever (lexical + dense-proxy RRF) and overlap rerank.

| Method | recall@5 |
|---|---|
| dense-only | see `tests/test_retrieval_evals.py` |
| hybrid + rerank | must be >= dense-only (CI gate) |

Postgres FTS + pgvector + BGE-M3 remain the production path once compose is available.
