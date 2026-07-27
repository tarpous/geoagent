"""STAC / Sentinel-2 imagery search and NDVI stats.

Default path uses committed Attica/Thessaloniki fixtures so CI and demos work
offline. A live Element84 Earth Search path is enabled when `pystac-client` is
installed and `GEOAGENT_STAC_LIVE=1`.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_CATALOG = ROOT / "data" / "fixtures" / "imagery" / "catalog.json"


@dataclass(slots=True)
class ImageryScene:
    scene_id: str
    datetime: str
    cloud_cover: float
    bbox: list[float]
    ndvi_mean: float
    ndvi_std: float
    source: str


def _load_fixture_catalog() -> list[dict[str, Any]]:
    if not FIXTURE_CATALOG.is_file():
        raise FileNotFoundError(f"missing imagery fixtures: {FIXTURE_CATALOG}")
    return json.loads(FIXTURE_CATALOG.read_text(encoding="utf-8"))["scenes"]


def _bbox_intersects(a: list[float], b: list[float]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def _ndvi_from_red_nir(red: list[list[float]], nir: list[list[float]]) -> tuple[float, float]:
    vals: list[float] = []
    for i, row in enumerate(red):
        for j, r in enumerate(row):
            n = nir[i][j]
            denom = n + r
            if denom == 0:
                continue
            vals.append((n - r) / denom)
    if not vals:
        return 0.0, 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return mean, math.sqrt(var)


def search_imagery(
    *,
    bbox: list[float],
    start_date: str,
    end_date: str,
    max_cloud: float = 40.0,
    live: bool | None = None,
) -> list[ImageryScene]:
    """Search imagery overlapping bbox in [min_lon, min_lat, max_lon, max_lat]."""
    use_live = live if live is not None else os.environ.get("GEOAGENT_STAC_LIVE") == "1"
    if use_live:
        try:
            return _search_live(bbox, start_date, end_date, max_cloud)
        except Exception as exc:  # noqa: BLE001
            # Fall back to fixtures rather than failing the swarm.
            scenes = _search_fixtures(bbox, start_date, end_date, max_cloud)
            for scene in scenes:
                scene.source = f"fixture(fallback:{type(exc).__name__})"
            return scenes
    return _search_fixtures(bbox, start_date, end_date, max_cloud)


def _search_fixtures(
    bbox: list[float],
    start_date: str,
    end_date: str,
    max_cloud: float,
) -> list[ImageryScene]:
    out: list[ImageryScene] = []
    for row in _load_fixture_catalog():
        if row["cloud_cover"] > max_cloud:
            continue
        if row["datetime"][:10] < start_date or row["datetime"][:10] > end_date:
            continue
        if not _bbox_intersects(bbox, row["bbox"]):
            continue
        red = row["red"]
        nir = row["nir"]
        mean, std = _ndvi_from_red_nir(red, nir)
        out.append(
            ImageryScene(
                scene_id=row["scene_id"],
                datetime=row["datetime"],
                cloud_cover=float(row["cloud_cover"]),
                bbox=list(row["bbox"]),
                ndvi_mean=mean,
                ndvi_std=std,
                source="fixture",
            )
        )
    return out


def _search_live(
    bbox: list[float],
    start_date: str,
    end_date: str,
    max_cloud: float,
) -> list[ImageryScene]:
    from pystac_client import Client

    client = Client.open("https://earth-search.aws.element84.com/v1")
    search = client.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
        max_items=5,
    )
    scenes: list[ImageryScene] = []
    for item in search.items():
        scenes.append(
            ImageryScene(
                scene_id=item.id,
                datetime=item.datetime.isoformat() if item.datetime else start_date,
                cloud_cover=float(item.properties.get("eo:cloud_cover", 100.0)),
                bbox=list(item.bbox or bbox),
                ndvi_mean=float("nan"),
                ndvi_std=float("nan"),
                source="live-stac",
            )
        )
    return scenes


def ndvi_composite_stats(
    *,
    bbox: list[float],
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    scenes = search_imagery(bbox=bbox, start_date=start_date, end_date=end_date)
    if not scenes:
        return {"ok": False, "error": "no_scenes", "scenes": []}
    means = [s.ndvi_mean for s in scenes if not math.isnan(s.ndvi_mean)]
    return {
        "ok": True,
        "scene_count": len(scenes),
        "ndvi_mean": sum(means) / len(means) if means else None,
        "scenes": [
            {
                "scene_id": s.scene_id,
                "datetime": s.datetime,
                "cloud_cover": s.cloud_cover,
                "ndvi_mean": s.ndvi_mean,
                "source": s.source,
            }
            for s in scenes
        ],
    }
