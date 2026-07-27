"""LangGraph wiring for the true peer swarm (transfer tools + parallel join).

No supervisor LLM. Peers invoke ``transfer_to_*`` tools; multi-target spawn is
executed as a concurrent wave then joined before the next specialist.
"""

from __future__ import annotations

from typing import Any, TypedDict

import ulid
from langgraph.graph import END, START, StateGraph

from geoagent.schemas.answer import FinalAnswer
from geoagent.schemas.handoff import Handoff
from geoagent.swarm.budget import load_budgets
from geoagent.swarm.graph import run_parallel_wave
from geoagent.swarm.intake import run_intake
from geoagent.swarm.policy import next_from_pending
from geoagent.swarm.specialists.cartographer import run_cartographer
from geoagent.swarm.specialists.critic import run_critic
from geoagent.swarm.specialists.earth_obs import run_earth_obs
from geoagent.swarm.specialists.geodata import run_geodata
from geoagent.swarm.specialists.librarian import run_librarian
from geoagent.swarm.state import TeamState
from geoagent.swarm.topology import SPECIALISTS
from geoagent.swarm.trace import TraceRecord


class GraphState(TypedDict, total=False):
    team: dict[str, Any]
    trace: dict[str, Any]


def _team(state: GraphState) -> TeamState:
    return TeamState.model_validate(state["team"])


def _load_trace(state: GraphState, trace_id: str) -> TraceRecord:
    data = state.get("trace") or {}
    trace = TraceRecord(trace_id=str(data.get("trace_id") or trace_id))
    trace.events = list(data.get("events") or [])
    trace.handoffs = list(data.get("handoffs") or [])
    trace.tool_calls = list(data.get("tool_calls") or [])
    trace.tool_call_parse_ok = int(data.get("tool_call_parse_ok") or 0)
    trace.tool_call_parse_total = int(data.get("tool_call_parse_total") or 0)
    trace.schema_ok = bool(data.get("schema_ok") or False)
    trace.final_answer = data.get("final_answer")
    return trace


def _dump_trace(trace: TraceRecord) -> dict[str, Any]:
    return {
        "trace_id": trace.trace_id,
        "events": trace.events,
        "handoffs": trace.handoffs,
        "tool_calls": trace.tool_calls,
        "tool_call_parse_ok": trace.tool_call_parse_ok,
        "tool_call_parse_total": trace.tool_call_parse_total,
        "schema_ok": trace.schema_ok,
        "final_answer": trace.final_answer,
    }


def _record_progress(before: TeamState, after: TeamState, trace: TraceRecord) -> None:
    for handoff in after.handoffs[len(trace.handoffs) :]:
        if isinstance(handoff, Handoff):
            trace.add_handoff(handoff)
        else:
            trace.add_handoff(Handoff.model_validate(handoff))
    for item in after.evidence[len(before.evidence) :]:
        tool = str(item.get("tool", "unknown"))
        ok = item.get("ok", True) is not False and "error" not in item
        trace.add_tool_call(
            before.active_agent,
            tool,
            {"summary": {k: v for k, v in item.items() if k != "result"}},
            ok=ok,
        )


def _drain_pending(team: TeamState) -> TeamState:
    if team.final_answer is not None or team.parallel_wave:
        return team
    if team.active_agent != "critic":
        return team
    nxt = next_from_pending(team)
    if nxt is not None:
        team.active_agent = nxt
        team.status = "running"
    return team


def _node(runner):
    def _run(state: GraphState) -> GraphState:
        team = _team(state)
        before = team.model_copy(deep=True)
        after = runner(team)
        # True swarm fan-out: execute concurrent peers before routing onward.
        if after.parallel_wave:
            after = run_parallel_wave(after)
        after = _drain_pending(after)
        trace = _load_trace(state, after.trace_id)
        _record_progress(before, after, trace)
        if after.final_answer is not None:
            trace.finalize(after.final_answer)
        return {"team": after.model_dump(mode="json"), "trace": _dump_trace(trace)}

    return _run


def _route(state: GraphState) -> str:
    team = _team(state)
    budgets = load_budgets()
    if team.final_answer is not None or team.status != "running":
        return END
    if team.steps >= budgets.max_swarm_steps:
        return END
    if team.active_agent not in SPECIALISTS:
        return END
    return team.active_agent


def build_langgraph():
    graph = StateGraph(GraphState)
    graph.add_node("intake", _node(run_intake))
    graph.add_node("geodata", _node(run_geodata))
    graph.add_node("earth-obs", _node(run_earth_obs))
    graph.add_node("librarian", _node(run_librarian))
    graph.add_node("cartographer", _node(run_cartographer))
    graph.add_node("critic", _node(run_critic))
    graph.add_edge(START, "intake")
    for name in ("intake", "geodata", "earth-obs", "librarian", "cartographer", "critic"):
        graph.add_conditional_edges(name, _route)
    return graph.compile()


_COMPILED = None


def get_graph():
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_langgraph()
    return _COMPILED


def run_swarm_langgraph(
    question: str,
    *,
    trace_id: str | None = None,
) -> tuple[FinalAnswer, TraceRecord]:
    tid = trace_id or str(ulid.new())
    team = TeamState(trace_id=tid, question=question)
    result = get_graph().invoke(
        {
            "team": team.model_dump(mode="json"),
            "trace": {
                "trace_id": tid,
                "events": [],
                "handoffs": [],
                "tool_calls": [],
                "tool_call_parse_ok": 0,
                "tool_call_parse_total": 0,
            },
        }
    )
    final_team = TeamState.model_validate(result["team"])
    if final_team.final_answer is None:
        final_team = run_critic(final_team)
    assert final_team.final_answer is not None
    trace = _load_trace(result, tid)
    if not trace.final_answer:
        trace.finalize(final_team.final_answer)
    return final_team.final_answer, trace
