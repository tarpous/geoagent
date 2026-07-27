"""Per-specialist transfer decisions (invokes handoff tools — not a supervisor).

CPU-only stand-in for each peer choosing among its ``transfer_to_*`` tools.
When local LLMs are enabled later, specialists keep the same tool catalog.
"""

from __future__ import annotations

import re
from typing import Any

from geoagent.schemas.handoff import SpecialistName
from geoagent.swarm.handoff_tools import (
    SwarmTransfer,
    apply_transfers,
    handoff_tools_for,
    transfer_tool_name,
)
from geoagent.swarm.state import TeamState
from geoagent.swarm.topology import DEFAULT_TOPOLOGY, SwarmTopology

_TREE = re.compile(r"tree\s*cover|ndvi|land\s*cover|imagery|satellite", re.I)
_DOC = re.compile(r"document|cite|planning|flood|corpus|policy", re.I)
_DETECT = re.compile(r"vehicle|building|detect|object", re.I)
_MAP = re.compile(r"\bmap\b|cartograph|draw|plot", re.I)


def _tools_used(state: TeamState) -> set[str]:
    return {
        str(item.get("tool"))
        for item in state.evidence
        if item.get("tool") and not item.get("handoff")
    }


def needs_geometry(state: TeamState) -> bool:
    return not any("geojson" in g for g in state.geometries)


def needs_imagery(state: TeamState) -> bool:
    q = state.question
    if not (_TREE.search(q) or _DETECT.search(q)):
        return False
    tools = _tools_used(state)
    return not tools.intersection({"stac_imagery", "landcover_classify", "detect_objects"})


def needs_docs(state: TeamState) -> bool:
    q = state.question
    tools = _tools_used(state)
    if "docs_search" in tools and state.citations:
        return False
    if state.numbers and not state.citations:
        return True
    if _DOC.search(q):
        return True
    if _TREE.search(q) or _DETECT.search(q):
        return "docs_search" not in tools
    return "docs_search" not in tools


def needs_map(state: TeamState) -> bool:
    tools = _tools_used(state)
    if "make_map" in tools:
        return False
    if state.geometries or _MAP.search(state.question) or state.numbers:
        return True
    return False


def needs_draft(state: TeamState) -> bool:
    return not state.draft_answer_md.strip()


def evidence_gaps(state: TeamState) -> dict[str, bool]:
    return {
        "geometry": needs_geometry(state),
        "imagery": needs_imagery(state),
        "docs": needs_docs(state),
        "map": needs_map(state),
        "draft": needs_draft(state),
    }


def parallel_peers_after_geodata(state: TeamState) -> list[SpecialistName]:
    peers: list[SpecialistName] = []
    if needs_imagery(state):
        peers.append("earth-obs")
    if needs_docs(state):
        peers.append("librarian")
    return peers


def decide_transfers(
    state: TeamState,
    *,
    from_agent: SpecialistName | None = None,
    topology: SwarmTopology | None = None,
    extra_delta: dict[str, Any] | None = None,
) -> SwarmTransfer:
    """Choose which ``transfer_to_*`` tools this peer invokes."""
    topo = topology or DEFAULT_TOPOLOGY
    src: SpecialistName = from_agent or state.active_agent
    catalog = handoff_tools_for(src, topology=topo)
    delta = dict(extra_delta or {})

    def transfer(dst: SpecialistName, reason: str) -> SwarmTransfer:
        tool = catalog.get(transfer_tool_name(dst))
        if tool is None:
            raise ValueError(f"{src} has no transfer tool for {dst}")
        return SwarmTransfer(handoffs=[tool.invoke(reason, **delta)])

    def spawn(peers: list[SpecialistName], reason: str, join: SpecialistName) -> SwarmTransfer:
        handoffs = []
        for dst in peers:
            tool = catalog.get(transfer_tool_name(dst))
            if tool is None:
                raise ValueError(f"{src} has no transfer tool for {dst}")
            handoffs.append(tool.invoke(reason, **delta))
        return SwarmTransfer(handoffs=handoffs, join=join)

    if src == "intake":
        imagery_intent = bool(
            needs_imagery(state) or _TREE.search(state.question) or _DETECT.search(state.question)
        )
        docs_only = bool(_DOC.search(state.question) and not imagery_intent)
        if docs_only:
            return transfer("librarian", "Document evidence required")
        if needs_geometry(state) or imagery_intent:
            return transfer("geodata", "Need AOI geometry before analysis")
        if needs_docs(state):
            return transfer("librarian", "Document evidence required")
        return transfer("geodata", "Spatial context required")

    if src == "geodata":
        peers = parallel_peers_after_geodata(state)
        if len(peers) >= 2:
            return spawn(peers, "Spawn independent analysis peers", join="cartographer")
        if peers:
            return transfer(peers[0], "Continue with required peer")
        if needs_map(state):
            return transfer("cartographer", "Geometry ready for mapping")
        return transfer("critic", "No further specialist work needed")

    if src == "earth-obs":
        if needs_docs(state):
            return transfer("librarian", "Need citation support from corpus")
        if needs_map(state):
            return transfer("cartographer", "Imagery ready for mapping")
        return transfer("critic", "Imagery complete; assemble answer")

    if src == "librarian":
        if needs_imagery(state):
            return transfer("earth-obs", "Documents ready; imagery still required")
        if needs_geometry(state):
            return transfer("geodata", "Need geometry before mapping")
        if needs_map(state) or needs_draft(state):
            return transfer("cartographer", "Evidence packet ready for mapping")
        return transfer("critic", "Document evidence sufficient")

    if src == "cartographer":
        return transfer("critic", "Draft ready for validation")

    raise ValueError(f"no transfer decision for agent {src}")


def transfer_control(
    state: TeamState,
    *,
    from_agent: SpecialistName | None = None,
    topology: SwarmTopology | None = None,
    extra_delta: dict[str, Any] | None = None,
) -> TeamState:
    """Invoke the specialist's chosen handoff tool(s) and update swarm state."""
    transfer = decide_transfers(
        state, from_agent=from_agent, topology=topology, extra_delta=extra_delta
    )
    return apply_transfers(state, transfer)


# Back-compat aliases used by earlier M3 helpers / tests.
def choose_next(
    state: TeamState,
    *,
    from_agent: SpecialistName | None = None,
    topology: SwarmTopology | None = None,
) -> tuple[SpecialistName, str]:
    transfer = decide_transfers(state, from_agent=from_agent, topology=topology)
    first = transfer.handoffs[0]
    return first.to, first.reason


def apply_peer_handoff(
    state: TeamState,
    *,
    from_agent: SpecialistName | None = None,
    topology: SwarmTopology | None = None,
    extra_delta: dict[str, Any] | None = None,
) -> TeamState:
    return transfer_control(
        state, from_agent=from_agent, topology=topology, extra_delta=extra_delta
    )


def next_from_pending(state: TeamState) -> SpecialistName | None:
    while state.pending_agents:
        peer = state.pending_agents.pop(0)
        if peer == "earth-obs" and needs_imagery(state):
            return peer
        if peer == "librarian" and needs_docs(state):
            return peer
        if peer == "cartographer" and needs_map(state):
            return peer
    return None
