# Geoagent Project Context

This file describes what the repository is and what it is intended to become. Operational workflow and environment policies live in `.cursor/rules/geoagent-conventions.mdc`.

## Project identity

Geoagent is a standalone, public, local-first geospatial analyst swarm. It answers questions over maps, satellite imagery, geospatial databases, and environmental/planning documents, returning evidence-backed answers with citations, measurements, geometries, and map artifacts.

The project is designed as an inspectable portfolio product for AI engineering, geospatial systems, RAG, multi-agent orchestration, MCP, evaluation, and local open-weight inference. Cloud LLM APIs are not runtime dependencies.

## Product surface

All clients use one shared swarm session API and one `FinalAnswer` contract:

- Custom Python TUI for interactive terminal analysis and streamed handoff traces.
- Web UI served through FastAPI, with SSE events, trace display, and map preview.
- MCP server exposing the geospatial tools and an `ask_swarm` tool.
- Optional Pi-custom terminal client that calls the swarm API; it is not a generic coding agent.

The hero question is:

> How much tree cover was lost within 2 km of the new ring road since 2023?

The initial demonstration regions are Attica and Thessaloniki.

## Architecture

The core is a LangGraph swarm with direct specialist handoffs, bounded reflection, typed state, and explicit budgets. The specialist roster is:

- `intake` — classifies the question and starts the team state.
- `geodata` — spatial SQL, OSM/PostGIS analysis, and geocoding.
- `earth-obs` — STAC imagery, NDVI, land-cover classification, and object detection.
- `librarian` — hybrid document retrieval and citation-grounded evidence.
- `cartographer` — maps and figures.
- `critic` — validates evidence, geometry, units, citations, and the assembled answer.

A single-agent implementation exists only as an ablation baseline. A supervisor architecture, A2A, and generic coding-agent behavior are outside the project scope.

## Locked runtime decisions

- Default inference backend: custom `llama.cpp` server.
- Serving and throughput comparison backend: vLLM.
- No Ollama, SGLang, or cloud chat API integration.
- Default demo models: Qwen3.5-9B for intake/critic/baseline; Gemma 4 E4B for specialists; Gemma Diffusion for factory drafts when available.
- Maximum model size is approximately 15B parameters for the 16 GB RTX 4080 Super target.
- Default quantization is Q4_K_M/Q5_K_M for GGUF and AWQ-4 or compatible INT4 for vLLM.
- Embeddings and reranking use BGE-M3 and bge-reranker-v2-m3, with CPU execution acceptable.
- Eval-factory runtime is the Pi SDK, separate from the product's optional Pi chat client.

## Core contracts

`FinalAnswer` is the only successful or refused turn result consumed by the critic, TUI, web UI, MCP, and evaluation code. It includes:

- Status: `answered`, `refused`, or `degraded`.
- Markdown answer and structured quantities with explicit units.
- Span- or quote-level citations.
- WGS84 GeoJSON geometries and optional map artifact.
- Refusal reason when applicable.
- Warnings and the model roster used.

Tool and agent structured output is schema-validated, preferably using backend-native JSON schema or grammar constraints. One repair retry is allowed; repeated violations produce a controlled failure rather than an infinite loop.

Geospatial data is stored and exchanged as EPSG:4326 WGS84. Metric operations use an appropriate projected CRS, defaulting to EPSG:2100 for Greece demo AOIs. Tools must declare units, time ranges, and timezone; geometry validators reject empty, non-finite, invalid, or out-of-scope geometries.

## Required capabilities

The tools layer must contain real implementations, not fixture-only stubs:

- Parameterized PostGIS/OSM spatial queries.
- STAC/Sentinel-2 imagery search, COG access, cloud masking, and NDVI composites.
- ONNX land-cover classification.
- ONNX object detection.
- Rate-limited, cached geocoding.
- Map generation with PNG/HTML artifacts.
- Hybrid document RAG using PostgreSQL full-text search, pgvector, reciprocal-rank fusion, and local reranking.

The evaluation system includes a factory, verifier, `golden@v1` dataset, human audit slice, retrieval metrics, schema/tool-call metrics, swarm-vs-single ablations, and llama.cpp-vs-vLLM measurements.

## Data and provenance

The project uses public geospatial and environmental/planning sources. OSM data requires ODbL attribution. Corpus documents, model weights, ONNX models, and third-party code require machine-readable manifests and license information. `NOTICE` and the relevant manifests are part of the shippable product.

CI must run offline against committed fixtures while preserving real tool and model paths. Fixtures are test data, not substitutes for production implementations or model inference.

## Repository shape

```text
src/geoagent/
  swarm/          LangGraph state, handoffs, budgets, and specialists
  baseline/       Single-agent ablation
  tools/          Geospatial and imagery tools
  rag/            Ingestion, chunking, retrieval, reranking, citations
  schemas/        FinalAnswer, events, handoffs, quantities
  geo/            CRS, units, and geometry validators
  llm/            OpenAI-compatible local backend client and structured output
  mcp_server/     MCP tools and ask_swarm
  tui/            Custom terminal client
  api/            FastAPI SSE API and web UI
  clients/pi_chat/ Optional Pi-custom client
configs/          Model profiles, seeds, temperatures, and quantization
deploy/           Docker Compose and llama.cpp/vLLM launch glue
data/             Fixtures, OSM attribution, and corpus manifests
models/           Licensed model locations and checksum metadata
evals/            Factory, golden set, judges, metrics, and results
tests/            Unit, geo, integration, safety, and client smoke tests
prompts/          Versioned system prompts
docs/             Architecture and geospatial correctness documentation
```

## Definition of done

The project is complete when `make demo` runs the Attica hero path, produces a validated `FinalAnswer`, trace, citations, and map artifact, and the same swarm core is usable through the TUI, web UI, and MCP. Tests, offline CI, evaluation gates, provenance manifests, `NOTICE`, reproducibility pins, and `REPORT.md` must also be shipped.

The source plan is `05-geoagent-agentic-rag.md`; it is the detailed specification when this context summary does not answer a design question.
