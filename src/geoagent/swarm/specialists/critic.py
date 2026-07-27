"""Critic specialist: validate draft into FinalAnswer with one bounded reflection."""

from __future__ import annotations

from pathlib import Path

from geoagent.geo.validate import GeometryValidationError, validate_geojson
from geoagent.schemas.answer import Citation, FinalAnswer, GeoRef, Refusal
from geoagent.schemas.handoff import SpecialistName
from geoagent.schemas.quantity import Quantity
from geoagent.swarm.budget import load_budgets
from geoagent.swarm.handoff_tools import SwarmTransfer, apply_transfers, create_handoff_tool
from geoagent.swarm.state import TeamState


def _domain_tools(state: TeamState) -> set[str]:
    return {
        str(item.get("tool"))
        for item in state.evidence
        if item.get("tool") and not item.get("handoff")
    }


def _choose_reflection_target(state: TeamState, warnings: list[str]) -> tuple[SpecialistName, str] | None:
    """Pick one peer to fix the worst gap. Returns None if nothing actionable."""
    tools = _domain_tools(state)
    q = state.question.lower()
    wants_imagery = any(k in q for k in ("tree", "cover", "ndvi", "vehicle", "detect", "imagery"))
    wants_docs = any(k in q for k in ("document", "cite", "planning", "flood")) or wants_imagery

    if wants_imagery and not state.numbers:
        return "earth-obs", "Reflection: missing quantitative imagery results"
    if wants_docs and not state.citations:
        return "librarian", "Reflection: citations missing or unresolved"
    if not any("geojson" in g for g in state.geometries):
        return "geodata", "Reflection: AOI geometry missing or invalid"
    if any(w.startswith("geometry dropped") for w in warnings):
        return "geodata", "Reflection: repair dropped geometries"
    if any(w.startswith("quantity dropped") for w in warnings):
        return "earth-obs", "Reflection: repair invalid quantities"
    if any(w.startswith("citation dropped") for w in warnings):
        return "librarian", "Reflection: repair invalid citations"
    if not state.draft_answer_md.strip() or "make_map" not in tools:
        return "cartographer", "Reflection: draft or map artifact incomplete"
    return None


def run_critic(state: TeamState, *, transfer: bool = True) -> TeamState:
    warnings = list(state.warnings)
    geometries: list[GeoRef] = []
    for geom in state.geometries:
        try:
            validate_geojson(geom["geojson"], require_demo_aoi=True)
            geometries.append(
                GeoRef(name=str(geom.get("name", "geom")), geojson=geom["geojson"], epsg_computed="EPSG:2100")
            )
        except (GeometryValidationError, KeyError, TypeError) as exc:
            warnings.append(f"geometry dropped: {exc}")

    numbers: list[Quantity] = []
    for raw in state.numbers:
        try:
            numbers.append(Quantity.model_validate(raw))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"quantity dropped: {exc}")

    citations: list[Citation] = []
    for raw in state.citations:
        try:
            citations.append(Citation.model_validate(raw))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"citation dropped: {exc}")

    map_artifact = None
    for item in state.evidence:
        if item.get("tool") == "make_map":
            arts = item.get("artifacts") or {}
            for key in ("png", "html", "geojson", "folium_html"):
                if arts.get(key):
                    map_artifact = Path(arts[key])
                    break

    budgets = load_budgets()
    bounce = _choose_reflection_target(state, warnings)
    if (
        transfer
        and bounce is not None
        and state.reflection_count < budgets.max_reflections
        and state.status == "running"
    ):
        target, reason = bounce
        state.reflection_count += 1
        state.warnings = warnings
        tool = create_handoff_tool(source="critic", destination=target)
        return apply_transfers(
            state,
            SwarmTransfer(handoffs=[tool.invoke(reason)]),
        )

    roster = {"swarm": "deterministic-cpu"}
    for agent in state.visited_agents:
        roster[agent] = "deterministic-cpu"
    roster["critic"] = "deterministic-cpu"

    if not state.draft_answer_md.strip() and not numbers:
        state.final_answer = FinalAnswer(
            trace_id=state.trace_id,
            status="refused",
            answer_md="",
            refusal=Refusal(reason_code="unanswerable", message="Insufficient evidence"),
            warnings=warnings,
            model_roster=roster,
        )
        state.status = "refused"
        return state

    status = "degraded" if warnings else "answered"
    state.final_answer = FinalAnswer(
        trace_id=state.trace_id,
        status=status,
        answer_md=state.draft_answer_md or "Answer assembled from tool evidence.",
        numbers=numbers,
        citations=citations,
        geometries=geometries,
        map_artifact=map_artifact,
        warnings=warnings,
        model_roster=roster,
    )
    state.status = "done" if status == "answered" else "degraded"
    state.active_agent = "critic"
    return state
