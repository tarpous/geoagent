"""M3 handoff and schema-trace tests."""

from evals.agent_evals import evaluate_hero_handoff
from geoagent.swarm import HERO_HANDOFF_PATH, handoff_correctness, run_swarm_with_trace


def test_hero_handoff_and_parse_rate():
    answer, trace = run_swarm_with_trace(
        "How much tree cover was lost within 2 km of the new ring road since 2023?"
    )
    assert answer.status in {"answered", "degraded"}
    assert trace.schema_ok is True
    assert trace.tool_call_parse_rate >= 0.95
    assert handoff_correctness(trace, HERO_HANDOFF_PATH) >= 0.8


def test_agent_evals_report_written():
    report = evaluate_hero_handoff()
    assert report["schema_ok"] is True
    assert report["tool_call_parse_rate"] >= 0.95
