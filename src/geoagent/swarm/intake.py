"""Intake specialist: classify question and seed team state."""

from __future__ import annotations

import re

from geoagent.swarm.policy import transfer_control
from geoagent.swarm.state import TeamState

_ATTICA = re.compile(r"attica|athens|ring\s*road", re.I)
_THESS = re.compile(r"thessaloniki|salonika", re.I)
_OUT_OF_AOI = re.compile(r"singapore|mangrove|amazonas|california|sydney", re.I)


def run_intake(state: TeamState, *, transfer: bool = True) -> TeamState:
    q = state.question
    if _OUT_OF_AOI.search(q) and not (_ATTICA.search(q) or _THESS.search(q)):
        from geoagent.schemas.answer import FinalAnswer, Refusal

        state.final_answer = FinalAnswer(
            trace_id=state.trace_id,
            status="refused",
            answer_md="",
            refusal=Refusal(
                reason_code="out_of_aoi",
                message="Question is outside the Attica/Thessaloniki demo AOIs.",
            ),
            model_roster={"intake": "deterministic-m3"},
        )
        state.status = "refused"
        state.active_agent = "critic"
        return state

    if _THESS.search(q):
        state.aoi = "Thessaloniki"
    elif _ATTICA.search(q):
        state.aoi = "Attica"
    else:
        state.aoi = "Attica"

    if not transfer:
        return state
    return transfer_control(state, from_agent="intake", extra_delta={"aoi": state.aoi})
