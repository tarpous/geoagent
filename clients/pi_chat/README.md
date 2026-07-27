# Optional Pi-custom terminal client

This client is **not** a generic coding agent. It only wraps the geoagent swarm
session API (`ask_swarm` / `/v1/ask`) so a Pi SDK session can ask geospatial
questions and show traces.

## Status

Scaffold only. No GPU/LLM dependency. Runtime wiring waits on Node/Pi SDK install
approval.

## Intended API surface

```ts
// ask_swarm(question: string) -> FinalAnswer JSON from POST /v1/ask
// show_trace(trace_id: string) -> events from the last ask payload
```

## Configure

```bash
GEOAGENT_API_BASE_URL=http://127.0.0.1:8088
```

See the product plan for the locked requirement that product Pi-chat never
imports the swarm package directly—only the HTTP session API.
