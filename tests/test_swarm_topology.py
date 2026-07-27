"""Tests for true peer-swarm: transfer tools, parallel join, topology."""

from __future__ import annotations

import pytest

from geoagent.swarm import (
    HERO_HANDOFF_PATH,
    handoff_correctness,
    run_swarm_with_trace,
    swarm_adjacency,
    topology_validity,
)
from geoagent.swarm.graph import handoff_path, transfer_catalog
from geoagent.swarm.handoff_tools import handoff_tools_for, transfer_tool_name
from geoagent.swarm.handoffs import handoff_to
from geoagent.swarm.state import TeamState
from geoagent.swarm.topology import DEFAULT_TOPOLOGY


def test_topology_rejects_illegal_edge():
    state = TeamState(trace_id="t", question="q", active_agent="intake")
    with pytest.raises(ValueError, match="not in swarm topology"):
        handoff_to(state, "cartographer", "skip ahead")


def test_transfer_tool_catalog_per_peer():
    tools = handoff_tools_for("geodata")
    assert transfer_tool_name("earth-obs") in tools
    assert transfer_tool_name("librarian") in tools
    catalog = transfer_catalog()
    assert "transfer_to_critic" in catalog["cartographer"]


def test_hero_parallel_swarm_path():
    answer, trace = run_swarm_with_trace(
        "How much tree cover was lost within 2 km of the new ring road since 2023?"
    )
    assert answer.status in {"answered", "degraded"}
    assert handoff_correctness(trace, HERO_HANDOFF_PATH) >= 0.8
    assert topology_validity(trace) == 1.0
    path = handoff_path(trace)
    assert "earth-obs" in path and "librarian" in path
    # Parallel spawn recorded as transfer tools from geodata.
    transfer_tools = [t["tool"] for t in trace.tool_calls if str(t["tool"]).startswith("transfer_to_")]
    assert "transfer_to_earth_obs" in transfer_tools
    assert "transfer_to_librarian" in transfer_tools
    assert any(t["tool"] == "swarm_join" for t in trace.tool_calls)


def test_document_question_skips_earth_obs():
    answer, trace = run_swarm_with_trace(
        "Cite Attica flood planning documents relevant to agricultural land."
    )
    path = handoff_path(trace)
    assert answer.status in {"answered", "degraded", "refused"}
    assert "librarian" in path
    assert "earth-obs" not in path
    assert topology_validity(trace) == 1.0


def test_swarm_adjacency_export():
    adj = swarm_adjacency()
    assert "geodata" in adj
    assert "earth-obs" in adj["geodata"]
    assert DEFAULT_TOPOLOGY.is_allowed("cartographer", "critic")
