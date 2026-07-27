"""Typed handoff messages between swarm specialists."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SpecialistName = Literal[
    "intake",
    "geodata",
    "earth-obs",
    "librarian",
    "cartographer",
    "critic",
]


class Handoff(BaseModel):
    """Direct specialist-to-specialist handoff (not free-text routing)."""

    model_config = ConfigDict(extra="forbid")

    to: SpecialistName
    reason: str = Field(min_length=1)
    state_delta: dict[str, Any] = Field(default_factory=dict)
