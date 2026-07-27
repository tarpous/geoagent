"""Deterministic swarm runner (LangGraph wiring lands next; handoff contract is fixed)."""

from __future__ import annotations

import ulid

from geoagent.schemas.answer import FinalAnswer
from geoagent.swarm.budget import load_budgets
from geoagent.swarm.intake import run_intake
from geoagent.swarm.specialists.cartographer import run_cartographer
from geoagent.swarm.specialists.critic import run_critic
from geoagent.swarm.specialists.earth_obs import run_earth_obs
from geoagent.swarm.specialists.geodata import run_geodata
from geoagent.swarm.specialists.librarian import run_librarian
from geoagent.swarm.state import TeamState

_RUNNERS = {
    "intake": run_intake,
    "geodata": run_geodata,
    "earth-obs": run_earth_obs,
    "librarian": run_librarian,
    "cartographer": run_cartographer,
    "critic": run_critic,
}


def run_swarm(question: str, *, trace_id: str | None = None) -> FinalAnswer:
    budgets = load_budgets()
    state = TeamState(
        trace_id=trace_id or str(ulid.new()),
        question=question,
    )
    while state.status == "running" and state.steps < budgets.max_swarm_steps:
        runner = _RUNNERS.get(state.active_agent)
        if runner is None:
            state.warnings.append(f"unknown agent: {state.active_agent}")
            state.status = "degraded"
            break
        before = state.active_agent
        state = runner(state)
        if state.active_agent == before and state.final_answer is None:
            state.warnings.append(f"agent made no progress: {before}")
            state.status = "degraded"
            break
        if state.tool_calls > budgets.max_tool_calls_per_specialist * 6:
            state.warnings.append("global tool-call budget exceeded")
            state.status = "degraded"
            break
        if state.final_answer is not None:
            break

    if state.final_answer is None:
        state = run_critic(state)
    assert state.final_answer is not None
    return state.final_answer
