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
    # Concurrent peer wave (true swarm fan-out); emptied after join.
    parallel_wave: list[SpecialistName] = Field(default_factory=list)
    join_agent: SpecialistName | None = None
    # Legacy sequential queue (drained only if parallel_wave is empty).
    pending_agents: list[SpecialistName] = Field(default_factory=list)
    visited_agents: list[SpecialistName] = Field(default_factory=list)
    steps: int = 0
    tool_calls: int = 0
    tool_calls_by_agent: dict[str, int] = Field(default_factory=dict)
    reflection_count: int = 0
    draft_answer_md: str = ""
    final_answer: FinalAnswer | None = None
    status: Literal["running", "done", "refused", "degraded"] = "running"

    def apply_handoff(self, handoff: Handoff) -> None:
        self.handoffs.append(handoff)
        if self.active_agent not in self.visited_agents:
            self.visited_agents.append(self.active_agent)
        self.active_agent = handoff.to
        self.pending_agents = [p for p in self.pending_agents if p != handoff.to]
        self.parallel_wave = [p for p in self.parallel_wave if p != handoff.to]
        for key, value in handoff.state_delta.items():
            if hasattr(self, key):
                setattr(self, key, value)
