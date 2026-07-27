# Deploy

## Database

```bash
# from repo root (Windows path to docker.exe may be needed until PATH is refreshed)
make db-up
make db-ingest
```

`deploy/docker-compose.yml` builds `geoagent-postgis-pgvector:16` (PostGIS + pgvector + FTS)
and exposes Postgres on `127.0.0.1:5432`.

Default DSN:

```text
postgresql://geoagent:geoagent@127.0.0.1:5432/geoagent
```

## LLM servers

llama.cpp and vLLM stay on the **host GPU**. See `deploy/llm/`. Compose services should use
`host.docker.internal` to reach them.

## Requirements

Docker Desktop must be running. On Windows this typically needs the WSL2 backend enabled.
