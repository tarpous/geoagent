"""Deterministic swarm runner with traces and handoff metrics.

LangGraph remains the target runtime; this runner preserves the same handoff
contract and FinalAnswer/trace outputs for evals and clients.
"""

from __future__ import annotations

from pathlib import Path

import ulid

from geoagent.schemas.answer import FinalAnswer
from geoagent.swarm.budget import load_budgets
from geoagent.swarm.intake import run_intake
from geoagent.swarm.specialists.cartographer import run_cartographer
from geoagent.swarm.specialists.critic import run_critic
from geoagent.swarm.specialists.earth_obs import run_earth_obs
from geoagent.swarm.specialists.geodata import run_geodata
from geoagent.swarm.specialists.librarian import run_librarian
from geoagent.swarm.state import TeamState
from geoagent.swarm.trace import TraceRecord

_RUNNERS = {
    "intake": run_intake,
    "geodata": run_geodata,
    "earth-obs": run_earth_obs,
    "librarian": run_librarian,
    "cartographer": run_cartographer,
    "critic": run_critic,
}

HERO_HANDOFF_PATH = ["intake", "geodata", "earth-obs", "librarian", "cartographer", "critic"]


def run_swarm(question: str, *, trace_id: str | None = None) -> FinalAnswer:
    answer, _trace = run_swarm_with_trace(question, trace_id=trace_id)
    return answer


def run_swarm_with_trace(
    question: str,
    *,
    trace_id: str | None = None,
    trace_dir: Path | None = None,
) -> tuple[FinalAnswer, TraceRecord]:
    budgets = load_budgets()
    tid = trace_id or str(ulid.new())
    state = TeamState(trace_id=tid, question=question)
    trace = TraceRecord(trace_id=tid)
    seen_handoffs = 0
    seen_evidence = 0

    while state.status == "running" and state.steps < budgets.max_swarm_steps:
        runner = _RUNNERS.get(state.active_agent)
        if runner is None:
            state.warnings.append(f"unknown agent: {state.active_agent}")
            state.status = "degraded"
            break
        before = state.active_agent
        state = runner(state)

        # Record new handoffs emitted by the specialist.
        for handoff in state.handoffs[seen_handoffs:]:
            trace.add_handoff(handoff)
        seen_handoffs = len(state.handoffs)

        # Record newly appended evidence as tool results.
        for item in state.evidence[seen_evidence:]:
            tool = str(item.get("tool", "unknown"))
            ok = item.get("ok", True) is not False and "error" not in item
            trace.add_tool_call(before, tool, {"summary": {k: v for k, v in item.items() if k != "result"}}, ok=ok)
        seen_evidence = len(state.evidence)

        if state.active_agent == before and state.final_answer is None:
            state.warnings.append(f"agent made no progress: {before}")
            state.status = "degraded"
            break
        if state.tool_calls > budgets.max_tool_calls_per_specialist * 6:
            state.warnings.append("global tool-call budget exceeded")
            state.status = "degraded"
            break
        if state.final_answer is not None:
            break

    if state.final_answer is None:
        state = run_critic(state)
    assert state.final_answer is not None
    trace.finalize(state.final_answer)
    if trace_dir is not None:
        trace.write(trace_dir / f"{tid}.json")
    return state.final_answer, trace


def handoff_path(trace: TraceRecord) -> list[str]:
    path = ["intake"]
    for handoff in trace.handoffs:
        path.append(str(handoff["to"]))
    return path


def handoff_correctness(trace: TraceRecord, expected: list[str] | None = None) -> float:
    expected = expected or HERO_HANDOFF_PATH
    actual = handoff_path(trace)
    if not expected:
        return 0.0
    matched = sum(1 for a, b in zip(actual, expected, strict=False) if a == b)
    return matched / max(len(expected), len(actual))
