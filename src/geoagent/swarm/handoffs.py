"""Handoff helpers."""

from __future__ import annotations

from typing import Any

from geoagent.schemas.handoff import Handoff, SpecialistName
from geoagent.swarm.state import TeamState


def handoff_to(
    state: TeamState,
    to: SpecialistName,
    reason: str,
    **state_delta: Any,
) -> TeamState:
    state.apply_handoff(Handoff(to=to, reason=reason, state_delta=state_delta))
    state.steps += 1
    return state
