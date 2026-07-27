"""Single-agent baseline: one agent, all tools, no handoffs."""

from __future__ import annotations

from pathlib import Path

import ulid

from geoagent.schemas.answer import Citation, FinalAnswer, GeoRef, Quantity
from geoagent.tools.detect import detection_summary
from geoagent.tools.docs_search import docs_search
from geoagent.tools.geocode import geocode
from geoagent.tools.landcover import tree_cover_loss_ha
from geoagent.tools.mapping import make_map
from geoagent.tools.spatial_sql import spatial_sql
from geoagent.tools.stac_imagery import ndvi_composite_stats

ROOT = Path(__file__).resolve().parents[3]


def run_single_agent(question: str, *, trace_id: str | None = None) -> FinalAnswer:
    """Ablation baseline that calls the full tool set in one shot."""
    tid = trace_id or str(ulid.new())
    warnings: list[str] = []
    numbers: list[Quantity] = []
    citations: list[Citation] = []
    geometries: list[GeoRef] = []

    try:
        geo = geocode("Athens Attica Greece", require_demo_aoi=True)
        lon, lat = geo.lon, geo.lat
        geometries.append(GeoRef(name="geocode", geojson=geo.geojson))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"geocode: {exc}")
        lon, lat = 23.72, 37.98

    buffered = spatial_sql("buffer_point_m", {"lon": lon, "lat": lat, "distance_m": 2000})
    if buffered.get("ok"):
        geometries.append(GeoRef(name="buffer_2km", geojson=buffered["geojson"], epsg_computed="EPSG:2100"))

    stats = ndvi_composite_stats(bbox=[23.70, 37.90, 23.80, 38.00], start_date="2023-01-01", end_date="2024-12-31")
    if stats.get("ndvi_mean") is not None:
        numbers.append(
            Quantity(name="ndvi_mean", value=float(stats["ndvi_mean"]), unit="dimensionless", source_tool="stac_imagery")
        )

    if "tree" in question.lower() or "cover" in question.lower():
        loss = tree_cover_loss_ha(
            before_scene_id="attica-ringroad-2023-04",
            after_scene_id="attica-ringroad-2024-06",
        )
        numbers.append(
            Quantity(
                name="tree_cover_loss",
                value=float(loss["tree_cover_loss_ha"]),
                unit="ha",
                source_tool="landcover_classify",
            )
        )

    if "vehicle" in question.lower() or "detect" in question.lower():
        det = detection_summary("attica-ringroad-2024-06")
        numbers.append(
            Quantity(
                name="vehicle_count",
                value=float(det["counts"].get("vehicle", 0)),
                unit="count",
                source_tool="detect_objects",
            )
        )

    docs = docs_search(question, top_k=3)
    for item in docs.get("evidence") or []:
        try:
            citations.append(Citation.model_validate(item["citation"]))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"citation: {exc}")

    artifacts = make_map(
        [{"name": g.name, "geojson": g.geojson} for g in geometries],
        out_dir=ROOT / "artifacts" / "demo" / tid,
        name="single",
    )
    loss = next((n for n in numbers if n.name == "tree_cover_loss"), None)
    answer_md = (
        f"Single-agent estimate of tree-cover loss is {loss.value:.2f} {loss.unit}."
        if loss
        else "Single-agent assembled tool outputs for the question."
    )
    return FinalAnswer(
        trace_id=tid,
        status="degraded" if warnings else "answered",
        answer_md=answer_md,
        numbers=numbers,
        citations=citations,
        geometries=geometries,
        map_artifact=artifacts.get("html") or artifacts.get("geojson"),
        warnings=warnings,
        model_roster={"baseline": "deterministic-single"},
    )
