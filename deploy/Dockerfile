# CPU-only application image. No GPU drivers; LLM servers stay on the host.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    GEOAGENT_SWARM_RUNTIME=loop \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY configs ./configs
COPY data ./data
COPY prompts ./prompts
COPY evals ./evals
COPY clients ./clients

RUN uv sync --frozen --no-dev

EXPOSE 8088
CMD ["geoagent", "api", "--host", "0.0.0.0", "--port", "8088"]
