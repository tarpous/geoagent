"""Librarian specialist."""

from __future__ import annotations

from geoagent.swarm.policy import transfer_control
from geoagent.swarm.state import TeamState
from geoagent.swarm.tool_allowlists import assert_tool_allowed
from geoagent.tools.docs_search import docs_search


def work_librarian(state: TeamState) -> TeamState:
    assert_tool_allowed("librarian", "docs_search")
    result = docs_search(state.question, top_k=3, prefer_postgres=True)
    state.tool_calls += 1
    state.evidence.append({"tool": "docs_search", "backend": result.get("backend")})
    for item in result.get("evidence") or []:
        state.citations.append(item["citation"])
    return state


def run_librarian(state: TeamState, *, transfer: bool = True) -> TeamState:
    state = work_librarian(state)
    if not transfer:
        if state.active_agent not in state.visited_agents:
            state.visited_agents.append(state.active_agent)
        return state
    return transfer_control(state, from_agent="librarian")
