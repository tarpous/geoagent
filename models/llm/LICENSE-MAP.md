# LLM license map

| Model family | Intended use in geoagent | License notes |
|---|---|---|
| Qwen3.5 | intake, critic, baseline, factory author | Record exact HF/GGUF license terms when weights are downloaded |
| Gemma 4 | specialists, verifier, judge | Record exact HF/GGUF license terms when weights are downloaded |
| Gemma Diffusion | factory draft stems (optional) | Fall back to Gemma 4 E4B if unavailable |
| BGE-M3 / bge-reranker-v2-m3 | embeddings and rerank | Record license terms when weights are downloaded |

Weight files are gitignored. Checksums and download scripts will live beside this map.
