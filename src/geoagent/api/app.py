"""FastAPI swarm session API and static web UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from geoagent.swarm import run_swarm_with_trace

UI_DIR = Path(__file__).resolve().parent / "ui"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    trace_id: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="geoagent", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/chat")
    def chat(req: ChatRequest) -> StreamingResponse:
        def event_stream() -> Iterator[str]:
            answer, trace = run_swarm_with_trace(req.question, trace_id=req.trace_id)
            for event in trace.events:
                yield _sse("event", event)
            payload: dict[str, Any] = {
                "final_answer": answer.model_dump(mode="json"),
                "tool_call_parse_rate": trace.tool_call_parse_rate,
                "schema_ok": trace.schema_ok,
            }
            yield _sse("done", payload)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/v1/ask")
    def ask(req: ChatRequest) -> dict[str, Any]:
        answer, trace = run_swarm_with_trace(req.question, trace_id=req.trace_id)
        return {
            "final_answer": answer.model_dump(mode="json"),
            "events": trace.events,
            "tool_call_parse_rate": trace.tool_call_parse_rate,
            "schema_ok": trace.schema_ok,
        }

    if UI_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

        @app.get("/", response_class=HTMLResponse)
        def index() -> HTMLResponse:
            return HTMLResponse((UI_DIR / "index.html").read_text(encoding="utf-8"))

    return app


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


app = create_app()
