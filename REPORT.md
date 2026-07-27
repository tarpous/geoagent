# geoagent REPORT

## Summary

`geoagent` is a local-first geospatial analyst swarm over maps, satellite imagery,
PostGIS/OSM analysis, and planning documents. The shared contract is a validated
`FinalAnswer` consumed by the critic, TUI, web UI, MCP, and evals.

## Architecture

- Swarm specialists: true peer swarm — `transfer_to_*` handoff tools, parallel earth-obs∥librarian join after geodata, topology-guarded (no commander)
- Single-agent baseline for ablation only
- Tools: geocode, allowlisted spatial SQL, STAC/NDVI fixtures, land-cover, detections,
  docs_search, make_map
- Clients: FastAPI (`/v1/ask`, `/v1/chat` SSE), Rich TUI, MCP (`ask_swarm` + tools)

## Evaluation

| Gate | Result (deterministic fixture path) |
|---|---|
| Hero handoff correctness | 1.0 |
| `tool_call_parse_rate` | 1.0 |
| `golden@v1` size | 100 items (+ 25 audit placeholders) |
| Swarm vs single | See `evals/results/ablation_swarm_vs_single.md` |
| llama.cpp vs vLLM tok/s | Pending host GPU servers |

## Contracts & geo rules

- Storage CRS: EPSG:4326; metric default EPSG:2100
- Structured output: schema validate + one repair retry policy in `llm/structured.py`
- Spatial SQL is template-allowlisted (no raw model SQL)

## Safety

- Injection / allowlist tests in `tests/test_safety.py`
- Handoff `state_delta` only applies known `TeamState` fields

## Licensing / provenance

See `NOTICE`, `data/osm/ATTRIBUTION`, `data/corpus_manifest.csv`, and
`models/*/LICENSE*`.

## Limits

- Default imagery/land-cover/detect paths are fixture-backed until pinned ONNX/STAC
  weights are downloaded (**GPU/weight gated**)
- Live LLM backends (llama.cpp / vLLM) are configured but not required for the
  deterministic demo path (**GPU gated**)
- Human audit κ uses placeholder labels until review
- Map artifacts always include GeoJSON + HTML + PNG on CPU; Folium HTML is optional

## Reproduce

```bash
uv sync --python 3.12 --extra dev
make db-up && make db-ingest   # optional Postgres hybrid RAG
make demo
make evals
geoagent tui --once "How much tree cover was lost within 2 km of the new ring road since 2023?"
geoagent api --port 8088
```
