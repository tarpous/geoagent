"""SSE / client stream event contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EventType = Literal[
    "handoff",
    "tool_call",
    "tool_result",
    "critic",
    "warning",
    "done",
]


class StreamEvent(BaseModel):
    """One event in the shared swarm session stream."""

    model_config = ConfigDict(extra="forbid")

    type: EventType
    trace_id: str = Field(min_length=1)
    agent: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
