"""Map artifact generation (static HTML via folium when available, else GeoJSON dump)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def make_map(
    layers: list[dict[str, Any]],
    *,
    out_dir: Path,
    name: str = "map",
    center: tuple[float, float] | None = None,
) -> dict[str, Path]:
    """Write map artifacts under out_dir. Returns paths for html and/or geojson."""
    out_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = out_dir / f"{name}.geojson"
    collection = {"type": "FeatureCollection", "features": []}
    for i, layer in enumerate(layers):
        geom = layer.get("geojson")
        if not geom:
            continue
        if geom.get("type") == "Feature":
            collection["features"].append(geom)
        elif geom.get("type") == "FeatureCollection":
            collection["features"].extend(geom.get("features") or [])
        else:
            collection["features"].append(
                {
                    "type": "Feature",
                    "properties": {"name": layer.get("name", f"layer-{i}")},
                    "geometry": geom,
                }
            )
    geojson_path.write_text(json.dumps(collection, indent=2), encoding="utf-8")

    artifacts: dict[str, Path] = {"geojson": geojson_path}
    try:
        import folium
    except ImportError:
        return artifacts

    if center is None:
        center = (37.98, 23.73)
    fmap = folium.Map(location=list(center), zoom_start=10)
    folium.GeoJson(collection).add_to(fmap)
    html_path = out_dir / f"{name}.html"
    fmap.save(str(html_path))
    artifacts["html"] = html_path
    return artifacts
