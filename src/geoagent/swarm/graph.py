"""True peer-swarm runner: transfer tools, parallel waves, topology guards.

Default runtime is the explicit swarm loop. Set GEOAGENT_SWARM_RUNTIME=langgraph
for the LangGraph compile. Neither path requires GPU/LLM inference.

Control moves only when a specialist invokes ``transfer_to_*`` handoff tools.
Multiple invokes = concurrent peers + join (no supervisor / commander).
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import ulid

from geoagent.schemas.answer import FinalAnswer
from geoagent.schemas.handoff import Handoff, SpecialistName
from geoagent.swarm.budget import load_budgets
from geoagent.swarm.intake import run_intake
from geoagent.swarm.merge import merge_team_states
from geoagent.swarm.policy import next_from_pending
from geoagent.swarm.specialists.cartographer import run_cartographer
from geoagent.swarm.specialists.critic import run_critic
from geoagent.swarm.specialists.earth_obs import run_earth_obs
from geoagent.swarm.specialists.geodata import run_geodata
from geoagent.swarm.specialists.librarian import run_librarian
from geoagent.swarm.state import TeamState
from geoagent.swarm.topology import DEFAULT_TOPOLOGY, validate_handoff_edge
from geoagent.swarm.trace import TraceRecord

_RUNNERS = {
    "intake": run_intake,
    "geodata": run_geodata,
    "earth-obs": run_earth_obs,
    "librarian": run_librarian,
    "cartographer": run_cartographer,
    "critic": run_critic,
}

# Hero path under true swarm with parallel earth-obs ∥ librarian after geodata.
HERO_HANDOFF_PATH = ["intake", "geodata", "earth-obs", "librarian", "cartographer", "critic"]


def run_swarm(question: str, *, trace_id: str | None = None) -> FinalAnswer:
    answer, _trace = run_swarm_with_trace(question, trace_id=trace_id)
    return answer


def _record_progress(
    trace: TraceRecord,
    before_agent: str,
    state: TeamState,
    *,
    seen_handoffs: int,
    seen_evidence: int,
) -> tuple[int, int]:
    for handoff in state.handoffs[seen_handoffs:]:
        trace.add_handoff(handoff)
    seen_handoffs = len(state.handoffs)
    for item in state.evidence[seen_evidence:]:
        tool = str(item.get("tool", "unknown"))
        ok = item.get("ok", True) is not False and "error" not in item
        trace.add_tool_call(
            before_agent,
            tool,
            {"summary": {k: v for k, v in item.items() if k != "result"}},
            ok=ok,
        )
    return seen_handoffs, len(state.evidence)


def run_parallel_wave(state: TeamState) -> TeamState:
    """Execute ``parallel_wave`` peers concurrently, merge, then activate join peer."""
    wave = list(state.parallel_wave)
    join: SpecialistName = state.join_agent or "cartographer"
    if not wave:
        return state

    base = state.model_copy(deep=True)
    base.parallel_wave = []
    base.join_agent = None

    def _run_peer(name: SpecialistName) -> TeamState:
        local = base.model_copy(deep=True)
        local.active_agent = name
        runner = _RUNNERS[name]
        return runner(local, transfer=False)

    parts: list[TeamState] = []
    with ThreadPoolExecutor(max_workers=max(1, len(wave))) as pool:
        futures = {pool.submit(_run_peer, name): name for name in wave}
        for fut in as_completed(futures):
            parts.append(fut.result())

    # Preserve spawn order when merging for stable traces.
    by_agent = {p.active_agent: p for p in parts}
    ordered = [by_agent[n] for n in wave if n in by_agent]
    merged = merge_team_states(base, *ordered)
    for name in wave:
        if name not in merged.visited_agents:
            merged.visited_agents.append(name)

    # Join barrier: peers finished → transfer to join specialist.
    if not DEFAULT_TOPOLOGY.is_allowed(wave[-1], join):
        # Fall back to any wave member that may legally join.
        src = next((n for n in wave if DEFAULT_TOPOLOGY.is_allowed(n, join)), wave[-1])
    else:
        src = wave[-1]
    DEFAULT_TOPOLOGY.assert_allowed(src, join)
    merged.handoffs.append(
        Handoff(
            to=join,
            reason="Parallel peer join",
            from_agent=src,
            tool_name="swarm_join",
        )
    )
    merged.evidence.append(
        {
            "tool": "swarm_join",
            "handoff": True,
            "to": join,
            "peers": list(wave),
        }
    )
    merged.active_agent = join
    merged.parallel_wave = []
    merged.join_agent = None
    merged.steps += 1
    return merged


def _drain_pending(state: TeamState) -> TeamState:
    if state.final_answer is not None or state.parallel_wave:
        return state
    if state.active_agent != "critic":
        return state
    nxt = next_from_pending(state)
    if nxt is not None:
        state.active_agent = nxt
        state.status = "running"
    return state


def run_swarm_with_trace(
    question: str,
    *,
    trace_id: str | None = None,
    trace_dir: Path | None = None,
) -> tuple[FinalAnswer, TraceRecord]:
    runtime = os.environ.get("GEOAGENT_SWARM_RUNTIME", "loop").lower()
    if runtime == "langgraph":
        from geoagent.swarm.langgraph_app import run_swarm_langgraph

        answer, trace = run_swarm_langgraph(question, trace_id=trace_id)
        if trace_dir is not None:
            trace.write(trace_dir / f"{trace.trace_id}.json")
        return answer, trace

    budgets = load_budgets()
    tid = trace_id or str(ulid.new())
    state = TeamState(trace_id=tid, question=question)
    trace = TraceRecord(trace_id=tid)
    seen_handoffs = 0
    seen_evidence = 0

    while state.status == "running" and state.steps < budgets.max_swarm_steps:
        if state.parallel_wave:
            before = ",".join(state.parallel_wave)
            state = run_parallel_wave(state)
            seen_handoffs, seen_evidence = _record_progress(
                trace, before, state, seen_handoffs=seen_handoffs, seen_evidence=seen_evidence
            )
            continue

        runner = _RUNNERS.get(state.active_agent)
        if runner is None:
            state.warnings.append(f"unknown agent: {state.active_agent}")
            state.status = "degraded"
            break
        before = state.active_agent
        calls_before = state.tool_calls
        state = runner(state)
        delta = max(0, state.tool_calls - calls_before)
        state.tool_calls_by_agent[before] = state.tool_calls_by_agent.get(before, 0) + delta
        if state.tool_calls_by_agent[before] > budgets.max_tool_calls_per_specialist:
            state.warnings.append(f"per-specialist tool budget exceeded: {before}")
            state.status = "degraded"
            break
        state = _drain_pending(state)
        seen_handoffs, seen_evidence = _record_progress(
            trace, before, state, seen_handoffs=seen_handoffs, seen_evidence=seen_evidence
        )

        if state.active_agent == before and not state.parallel_wave and state.final_answer is None:
            state.warnings.append(f"agent made no progress: {before}")
            state.status = "degraded"
            break
        if state.tool_calls > budgets.max_tool_calls_per_specialist * 6:
            state.warnings.append("global tool-call budget exceeded")
            state.status = "degraded"
            break
        if state.final_answer is not None:
            break

    # Drain reflection / unfinished peers; final assemble without further bounce.
    guard = 0
    while state.final_answer is None and guard < 8 and state.steps < budgets.max_swarm_steps:
        guard += 1
        if state.parallel_wave:
            state = run_parallel_wave(state)
            continue
        before = state.active_agent
        runner = _RUNNERS.get(before, run_critic)
        state = runner(state)
        if state.final_answer is not None:
            break
        if state.active_agent == before and not state.parallel_wave:
            state = run_critic(state, transfer=False)
            break
    if state.final_answer is None:
        state = run_critic(state, transfer=False)
    assert state.final_answer is not None
    # Catch up trace for drain phase.
    seen_handoffs, seen_evidence = _record_progress(
        trace,
        state.active_agent,
        state,
        seen_handoffs=seen_handoffs,
        seen_evidence=seen_evidence,
    )
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
    """Path overlap vs an expected sequence (hero ablation helper)."""
    expected = expected or HERO_HANDOFF_PATH
    actual = handoff_path(trace)
    if not expected:
        return 0.0
    matched = sum(1 for a, b in zip(actual, expected, strict=False) if a == b)
    return matched / max(len(expected), len(actual))


def topology_validity(trace: TraceRecord) -> float:
    """Fraction of handoffs that respect the engineered swarm graph.

    ``swarm_join`` is valid when the destination is allowed from any listed peer.
    """
    if not trace.handoffs:
        return 1.0
    ok = 0
    total = 0
    # Reconstruct source from from_agent when present; else infer from prior destination.
    prev: SpecialistName | str = "intake"
    for handoff in trace.handoffs:
        total += 1
        dst = handoff["to"]
        src = handoff.get("from_agent") or prev
        tool = handoff.get("tool_name")
        if tool == "swarm_join":
            # Join edges are legal if destination is reachable from the declaring peer.
            if validate_handoff_edge(src, dst):  # type: ignore[arg-type]
                ok += 1
        elif validate_handoff_edge(src, dst):  # type: ignore[arg-type]
            ok += 1
        prev = dst
    return ok / total if total else 1.0


def swarm_adjacency() -> dict[str, list[str]]:
    return DEFAULT_TOPOLOGY.as_adjacency()


def transfer_catalog() -> dict[str, list[str]]:
    """Map each specialist to its ``transfer_to_*`` tool names."""
    from geoagent.swarm.handoff_tools import handoff_tools_for

    return {name: sorted(handoff_tools_for(name)) for name in _RUNNERS if name != "critic"}
