"""Map artifact generation: GeoJSON + static HTML + minimal PNG (CPU-only)."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any


def _bbox(features: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []

    def _walk(coords: Any) -> None:
        if not coords:
            return
        if isinstance(coords[0], (int, float)) and len(coords) >= 2:
            xs.append(float(coords[0]))
            ys.append(float(coords[1]))
            return
        for item in coords:
            _walk(item)

    for feat in features:
        geom = feat.get("geometry") or {}
        _walk(geom.get("coordinates"))
    if not xs:
        return 23.5, 37.8, 24.0, 38.2
    return min(xs), min(ys), max(xs), max(ys)


def _write_png(path: Path, width: int, height: int, rgb: bytes) -> None:
    """Write an uncompressed RGB PNG without third-party deps."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + rgb[i * width * 3 : (i + 1) * width * 3] for i in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def _render_png(features: list[dict[str, Any]], path: Path, size: int = 256) -> Path:
    minx, miny, maxx, maxy = _bbox(features)
    pad = 0.05
    minx -= (maxx - minx) * pad or 0.01
    maxx += (maxx - minx) * pad or 0.01
    miny -= (maxy - miny) * pad or 0.01
    maxy += (maxy - miny) * pad or 0.01
    pixels = bytearray([235, 242, 248] * size * size)

    def project(lon: float, lat: float) -> tuple[int, int]:
        x = int((lon - minx) / (maxx - minx + 1e-12) * (size - 1))
        y = int((1.0 - (lat - miny) / (maxy - miny + 1e-12)) * (size - 1))
        return max(0, min(size - 1, x)), max(0, min(size - 1, y))

    def put(x: int, y: int, color: tuple[int, int, int]) -> None:
        idx = (y * size + x) * 3
        pixels[idx : idx + 3] = bytes(color)

    for feat in features:
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if gtype == "Point" and coords:
            x, y = project(float(coords[0]), float(coords[1]))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    put(max(0, min(size - 1, x + dx)), max(0, min(size - 1, y + dy)), (20, 90, 50))
        elif gtype in {"LineString", "MultiLineString", "Polygon", "MultiPolygon"} and coords:
            # Sample vertices only — enough for a demo thumbnail.
            flat: list[Any] = [coords]
            while flat and not isinstance(flat[0], (int, float)):
                nxt: list[Any] = []
                for item in flat:
                    if isinstance(item, list) and item and isinstance(item[0], (int, float)):
                        x, y = project(float(item[0]), float(item[1]))
                        put(x, y, (30, 100, 180))
                    elif isinstance(item, list):
                        nxt.extend(item)
                flat = nxt
    _write_png(path, size, size, bytes(pixels))
    return path


def _write_html(collection: dict[str, Any], path: Path, center: tuple[float, float]) -> Path:
    payload = json.dumps(collection)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>geoagent map</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    body {{ margin: 0; font-family: Georgia, serif; background: #0f1c17; color: #e8f0ea; }}
    header {{ padding: 1rem 1.25rem; border-bottom: 1px solid #2a4036; }}
    #map {{ height: calc(100vh - 64px); }}
    pre {{ margin: 0; padding: 1rem; overflow: auto; font-size: 12px; }}
  </style>
</head>
<body>
  <header>geoagent map · center {center[0]:.4f}, {center[1]:.4f}</header>
  <div id="map"><pre id="geojson"></pre></div>
  <script>
    const data = {payload};
    document.getElementById('geojson').textContent = JSON.stringify(data, null, 2);
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return path


def make_map(
    layers: list[dict[str, Any]],
    *,
    out_dir: Path,
    name: str = "map",
    center: tuple[float, float] | None = None,
) -> dict[str, Path]:
    """Write map artifacts under out_dir. Always produces geojson + html + png."""
    out_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = out_dir / f"{name}.geojson"
    collection: dict[str, Any] = {"type": "FeatureCollection", "features": []}
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

    if center is None:
        minx, miny, maxx, maxy = _bbox(collection["features"])
        center = ((miny + maxy) / 2.0, (minx + maxx) / 2.0)

    html_path = _write_html(collection, out_dir / f"{name}.html", center)
    png_path = _render_png(collection["features"], out_dir / f"{name}.png")

    artifacts: dict[str, Path] = {
        "geojson": geojson_path,
        "html": html_path,
        "png": png_path,
    }

    # Optional Folium enrichment when installed (never required).
    try:
        import folium

        fmap = folium.Map(location=list(center), zoom_start=10)
        folium.GeoJson(collection).add_to(fmap)
        folium_path = out_dir / f"{name}.folium.html"
        fmap.save(str(folium_path))
        artifacts["folium_html"] = folium_path
    except ImportError:
        pass

    return artifacts
