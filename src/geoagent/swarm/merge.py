"""Team-state merge for parallel swarm peers."""

from __future__ import annotations

from geoagent.swarm.state import TeamState


def merge_team_states(base: TeamState, *parts: TeamState) -> TeamState:
    """Merge parallel peer outputs into ``base`` (list fields append, scalars take max/last)."""
    out = base.model_copy(deep=True)
    for part in parts:
        out.evidence.extend(part.evidence[len(base.evidence) :])
        out.geometries.extend(part.geometries[len(base.geometries) :])
        out.numbers.extend(part.numbers[len(base.numbers) :])
        out.citations.extend(part.citations[len(base.citations) :])
        out.warnings.extend(w for w in part.warnings if w not in out.warnings)
        for agent in part.visited_agents:
            if agent not in out.visited_agents:
                out.visited_agents.append(agent)
        # Peer-local handoffs beyond the spawn wave are unusual; keep domain work only.
        out.tool_calls = max(out.tool_calls, part.tool_calls)
        out.steps = max(out.steps, part.steps)
        if part.draft_answer_md and len(part.draft_answer_md) > len(out.draft_answer_md):
            out.draft_answer_md = part.draft_answer_md
        if part.aoi and not out.aoi:
            out.aoi = part.aoi
        if part.final_answer is not None:
            out.final_answer = part.final_answer
            out.status = part.status
    out.parallel_wave = []
    return out
