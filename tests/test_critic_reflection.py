"""Bounded critic reflection tests."""

from __future__ import annotations

from geoagent.swarm.specialists.critic import run_critic
from geoagent.swarm.state import TeamState


def test_critic_reflects_once_for_missing_citations():
    state = TeamState(
        trace_id="t-reflect",
        question="How much tree cover was lost within 2 km of the new ring road since 2023?",
        active_agent="critic",
        draft_answer_md="Draft without citations.",
        numbers=[{"name": "tree_cover_loss", "value": 0.07, "unit": "ha", "source_tool": "landcover_classify"}],
        geometries=[{"name": "pt", "geojson": {"type": "Point", "coordinates": [23.72, 37.98]}}],
        evidence=[{"tool": "make_map", "artifacts": {"geojson": "x.geojson"}}],
        reflection_count=0,
    )
    after = run_critic(state)
    assert after.final_answer is None
    assert after.reflection_count == 1
    assert after.active_agent == "librarian"
    assert any(h.to == "librarian" for h in after.handoffs)


def test_critic_does_not_reflect_twice():
    state = TeamState(
        trace_id="t-reflect-2",
        question="How much tree cover was lost within 2 km of the new ring road since 2023?",
        active_agent="critic",
        draft_answer_md="Draft without citations.",
        numbers=[{"name": "tree_cover_loss", "value": 0.07, "unit": "ha", "source_tool": "landcover_classify"}],
        geometries=[{"name": "pt", "geojson": {"type": "Point", "coordinates": [23.72, 37.98]}}],
        evidence=[{"tool": "make_map", "artifacts": {"geojson": "x.geojson"}}],
        reflection_count=1,
    )
    after = run_critic(state)
    assert after.final_answer is not None
    assert after.final_answer.status in {"answered", "degraded"}
