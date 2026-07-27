# geoagent

Local-first geospatial analyst swarm. Ask questions over maps, satellite imagery, PostGIS/OSM data, and planning documents; get an evidence-backed `FinalAnswer` with citations, quantities, geometries, and map artifacts.

No cloud chat APIs are required at runtime. Demo regions: Attica and Thessaloniki.

**Hero question:** *How much tree cover was lost within 2 km of the new ring road since 2023?*

## What you get

| Surface | Entry |
| --- | --- |
| Swarm session API | `POST /v1/ask`, `POST /v1/chat` (SSE) |
| Web UI | FastAPI static UI + trace + map preview |
| Terminal | `geoagent tui` |
| MCP | `geoagent mcp` (`ask_swarm` + geospatial tools) |
| Optional Pi client | `clients/pi_chat/` (HTTP only; not a coding agent) |

All clients share one swarm core and one `FinalAnswer` contract.

## Swarm architecture

Peer handoff swarm (no supervisor):

- Specialists: `intake` → `geodata` → (`earth-obs` ∥ `librarian`) → `cartographer` → `critic`
- Control moves via `transfer_to_*` handoff tools (topology-guarded)
- Parallel fan-out/join after geodata when imagery and documents are both needed
- Critic may bounce work back **once** (bounded reflection)
- Single-agent baseline exists only for ablation

Offline/CI path is deterministic (fixtures, no GPU). Live local LLMs (llama.cpp default, vLLM ablation) are optional and capped at ~15B parameters.

Details: [`docs/architecture.md`](docs/architecture.md) · full spec: [`05-geoagent-agentic-rag.md`](05-geoagent-agentic-rag.md) · context: [`AGENTS.md`](AGENTS.md)

## Quick start (CPU / fixtures)

Requires Python 3.12 and [uv](https://github.com/astral-sh/uv).

```bash
uv sync --python 3.12 --extra dev
make demo          # Attica hero path → artifacts/demo/<trace_id>/
make test          # offline pytest
```

Useful commands:

```bash
make api           # http://127.0.0.1:8088
make tui
make mcp
make db-up         # PostGIS + pgvector (Docker)
make db-ingest
make evals
make model-plan    # print download plan only (does not fetch weights)
```

Environment knobs:

| Variable | Meaning |
| --- | --- |
| `GEOAGENT_SWARM_RUNTIME=loop` | Default peer-swarm loop |
| `GEOAGENT_SWARM_RUNTIME=langgraph` | Same specialists via LangGraph |
| `GEOAGENT_DATABASE_URL` | Postgres URL for hybrid RAG |

Copy `.env.example` for local overrides. Never commit `.env`, model weights, or `.venv`.

## Repository layout

```text
src/geoagent/   swarm, tools, rag, api, tui, mcp, schemas, llm
clients/        optional Pi-chat HTTP client
configs/        model profiles, budgets, seeds
deploy/         Compose (db + api), Dockerfiles
data/           fixtures, corpus manifests, OSM attribution
evals/          factory, golden@v1, judges, metrics
prompts/        versioned specialist prompts
tests/          unit, geo, integration, safety
docs/           architecture and geospatial notes
```

## Status

Shipped for the deterministic fixture path: schemas and geo validators, hybrid RAG (memory + Postgres), geospatial/imagery/doc tools, peer swarm with traces, `golden@v1` + swarm-vs-single ablation scaffolding, FastAPI/TUI/MCP clients, safety tests, offline CI, and `REPORT.md`.

Still optional / gated on local GPU or installs: llama.cpp and vLLM servers, HF weight downloads, live ONNX weights, Pi SDK eval-factory runtime, LLM-as-judge.

Reproduce notes and gates: [`REPORT.md`](REPORT.md) · licensing: [`NOTICE`](NOTICE)

## License

Apache-2.0. Third-party notices and data licenses are listed in `NOTICE` and under `data/` / `models/*/LICENSE*`.
