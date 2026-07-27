"""Librarian specialist."""

from __future__ import annotations

from geoagent.tools.docs_search import docs_search
from geoagent.swarm.handoffs import handoff_to
from geoagent.swarm.state import TeamState


def run_librarian(state: TeamState) -> TeamState:
    result = docs_search(state.question, top_k=3, prefer_postgres=True)
    state.tool_calls += 1
    state.evidence.append({"tool": "docs_search", "backend": result.get("backend")})
    for item in result.get("evidence") or []:
        state.citations.append(item["citation"])
    return handoff_to(state, "cartographer", "Evidence packet ready for mapping")
