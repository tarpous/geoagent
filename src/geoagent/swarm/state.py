"""Typed swarm team state."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from geoagent.schemas.answer import FinalAnswer
from geoagent.schemas.handoff import Handoff, SpecialistName

SpecialistStatus = Literal["idle", "running", "done", "failed"]


class TeamState(BaseModel):
    """Shared state passed across specialist handoffs."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    question: str
    active_agent: SpecialistName = "intake"
    aoi: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    geometries: list[dict[str, Any]] = Field(default_factory=list)
    numbers: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    handoffs: list[Handoff] = Field(default_factory=list)
    steps: int = 0
    tool_calls: int = 0
    draft_answer_md: str = ""
    final_answer: FinalAnswer | None = None
    status: Literal["running", "done", "refused", "degraded"] = "running"

    def apply_handoff(self, handoff: Handoff) -> None:
        self.handoffs.append(handoff)
        self.active_agent = handoff.to
        for key, value in handoff.state_delta.items():
            if hasattr(self, key):
                setattr(self, key, value)
