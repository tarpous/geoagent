"""Legacy single-edge handoff helper (tests + simple callers)."""

from __future__ import annotations

from typing import Any

from geoagent.schemas.handoff import SpecialistName
from geoagent.swarm.handoff_tools import SwarmTransfer, apply_transfers, create_handoff_tool
from geoagent.swarm.state import TeamState
from geoagent.swarm.topology import DEFAULT_TOPOLOGY, SwarmTopology


def handoff_to(
    state: TeamState,
    to: SpecialistName,
    reason: str,
    *,
    topology: SwarmTopology | None = None,
    from_agent: SpecialistName | None = None,
    **state_delta: Any,
) -> TeamState:
    """Invoke a single ``transfer_to_*`` tool toward ``to``."""
    topo = topology or DEFAULT_TOPOLOGY
    src: SpecialistName = from_agent or state.active_agent
    topo.assert_allowed(src, to)
    tool = create_handoff_tool(source=src, destination=to)
    return apply_transfers(state, SwarmTransfer(handoffs=[tool.invoke(reason, **state_delta)]))
