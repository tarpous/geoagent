"""First-class swarm handoff tools (langgraph-swarm / OpenAI Swarm style).

Each specialist owns ``transfer_to_<peer>`` tools for topology-allowed peers.
Invoking one or more tools is how control moves — there is no supervisor node.
Multi-target invoke = parallel spawn + join (true swarm fan-out).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from geoagent.schemas.handoff import Handoff, SpecialistName
from geoagent.swarm.state import TeamState
from geoagent.swarm.topology import DEFAULT_TOPOLOGY, SwarmTopology

_WS = re.compile(r"[\s\-]+")


def transfer_tool_name(destination: SpecialistName) -> str:
    return f"transfer_to_{_WS.sub('_', destination).lower()}"


@dataclass(frozen=True)
class HandoffTool:
    """A peer-transfer tool available to one specialist."""

    destination: SpecialistName
    name: str
    description: str
    source: SpecialistName

    def invoke(self, reason: str, **state_delta: Any) -> Handoff:
        return Handoff(
            to=self.destination,
            reason=reason,
            state_delta=state_delta,
            from_agent=self.source,
            tool_name=self.name,
        )


def create_handoff_tool(
    *,
    source: SpecialistName,
    destination: SpecialistName,
    description: str | None = None,
) -> HandoffTool:
    name = transfer_tool_name(destination)
    desc = description or f"Transfer control to peer specialist '{destination}'."
    return HandoffTool(destination=destination, name=name, description=desc, source=source)


def handoff_tools_for(
    source: SpecialistName,
    *,
    topology: SwarmTopology | None = None,
) -> dict[str, HandoffTool]:
    topo = topology or DEFAULT_TOPOLOGY
    tools = {
        create_handoff_tool(source=source, destination=dst)
        for dst in sorted(topo.allowed(source))
    }
    return {t.name: t for t in tools}


@dataclass
class SwarmTransfer:
    """Result of a specialist invoking one or more handoff tools."""

    handoffs: list[Handoff]
    join: SpecialistName | None = None

    @property
    def destinations(self) -> list[SpecialistName]:
        return [h.to for h in self.handoffs]

    @property
    def is_parallel(self) -> bool:
        return len(self.handoffs) > 1


def apply_transfers(state: TeamState, transfer: SwarmTransfer) -> TeamState:
    """Apply transfer tool results onto team state.

    Single target → classic active_agent handoff.
    Multiple targets → parallel_wave for concurrent peers; optional join peer.
    """
    if not transfer.handoffs:
        raise ValueError("swarm transfer requires at least one handoff tool invoke")

    src = state.active_agent
    for handoff in transfer.handoffs:
        DEFAULT_TOPOLOGY.assert_allowed(src, handoff.to)
        # Record every transfer tool call as a handoff event.
        state.handoffs.append(handoff)
        state.evidence.append(
            {
                "tool": handoff.tool_name or transfer_tool_name(handoff.to),
                "handoff": True,
                "to": handoff.to,
                "reason": handoff.reason,
            }
        )
        state.tool_calls += 1

    if src not in state.visited_agents:
        state.visited_agents.append(src)
    state.steps += 1

    if transfer.is_parallel:
        state.parallel_wave = list(transfer.destinations)
        state.join_agent = transfer.join
        state.active_agent = transfer.destinations[0]
        state.pending_agents = []
    else:
        only = transfer.handoffs[0]
        state.active_agent = only.to
        state.parallel_wave = []
        state.join_agent = None
        for key, value in only.state_delta.items():
            if hasattr(state, key):
                setattr(state, key, value)
    return state
