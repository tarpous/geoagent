# geoagent

Local-first geospatial analyst swarm. Ask multi-tool questions over maps, satellite imagery, PostGIS/OSM data, and planning documents; get evidence-backed answers with citations, quantities, geometries, and map artifacts.

Repository: https://github.com/tarpous/geoagent-swarm

## Clients

One shared swarm session API and one `FinalAnswer` contract:

- Custom Python TUI
- FastAPI web UI with SSE traces and map preview
- MCP server (`ask_swarm` + geospatial tools)

## Runtime

- Default LLM backend: custom `llama.cpp` server
- Serving / ablation backend: vLLM
- No cloud chat APIs in the default path
- Demo AOIs: Attica and Thessaloniki
- Hero path: tree-cover loss within 2 km of a ring road since 2023

## Quick start

```bash
# create / use the repo venv (Python 3.12)
uv sync --python 3.12 --extra dev

# dry-run demo against fixtures (M0+)
make demo
```

See `AGENTS.md` for project context and `05-geoagent-agentic-rag.md` for the full specification.

## Status

- **M0a** — package layout, locked configs, provenance stubs, demo dry-run
- **M0b** — `FinalAnswer` schemas, geo validators, structured-output repair path
- **M0c** — llama.cpp/vLLM launch scripts, golden seed factory (10 items), swarm budgets
- **M1a** — fixture-backed chunkers, hybrid RRF retriever, offline recall@5 gate
- **M1b** — Compose PostGIS/pgvector schema, Postgres hybrid retriever, corpus ingest
- **M2a** — geocode (cached), allowlisted spatial SQL, map GeoJSON/HTML artifacts

