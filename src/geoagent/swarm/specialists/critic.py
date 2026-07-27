"""Critic specialist: validate draft into FinalAnswer."""

from __future__ import annotations

from pathlib import Path

from geoagent.geo.validate import GeometryValidationError, validate_geojson
from geoagent.schemas.answer import Citation, FinalAnswer, GeoRef, Refusal
from geoagent.schemas.quantity import Quantity
from geoagent.swarm.state import TeamState


def run_critic(state: TeamState) -> TeamState:
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
            if arts.get("html"):
                map_artifact = Path(arts["html"])
            elif arts.get("geojson"):
                map_artifact = Path(arts["geojson"])

    if not state.draft_answer_md.strip() and not numbers:
        state.final_answer = FinalAnswer(
            trace_id=state.trace_id,
            status="refused",
            answer_md="",
            refusal=Refusal(reason_code="unanswerable", message="Insufficient evidence"),
            warnings=warnings,
            model_roster={"swarm": "deterministic-m3"},
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
        model_roster={"swarm": "deterministic-m3"},
    )
    state.status = "done" if status == "answered" else "degraded"
    state.active_agent = "critic"
    return state
