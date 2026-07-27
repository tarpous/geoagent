"""LangGraph runtime and out-of-AOI refusal tests (CPU-only)."""

from __future__ import annotations

from geoagent.swarm import handoff_correctness, run_swarm, run_swarm_with_trace


def test_langgraph_runtime_hero(monkeypatch):
    monkeypatch.setenv("GEOAGENT_SWARM_RUNTIME", "langgraph")
    answer, trace = run_swarm_with_trace(
        "How much tree cover was lost within 2 km of the new ring road since 2023?"
    )
    assert answer.status in {"answered", "degraded"}
    assert trace.schema_ok is True
    assert any(n.name == "tree_cover_loss" for n in answer.numbers)
    assert handoff_correctness(trace) >= 0.8


def test_out_of_aoi_refusal(monkeypatch):
    monkeypatch.delenv("GEOAGENT_SWARM_RUNTIME", raising=False)
    answer = run_swarm("Measure mangrove loss near Singapore since 2020.")
    assert answer.status == "refused"
    assert answer.refusal is not None
    assert answer.refusal.reason_code == "out_of_aoi"
