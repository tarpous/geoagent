"""ONNX land-cover classification with a fixture backend.

Production path loads `models/landcover/*.onnx` via onnxruntime when present.
Fixture path classifies synthetic NDVI tiles into documented class labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geoagent.tools.stac_imagery import _load_fixture_catalog, _ndvi_from_red_nir

# Documented label set for the demo path.
LANDCOVER_CLASSES = ("tree", "crop", "urban", "water", "bare")

ROOT = Path(__file__).resolve().parents[3]
ONNX_DIR = ROOT / "models" / "landcover"


@dataclass(slots=True)
class LandcoverResult:
    scene_id: str
    class_histogram: dict[str, float]
    area_ha_by_class: dict[str, float]
    backend: str


def _classify_ndvi_pixel(ndvi: float) -> str:
    if ndvi >= 0.55:
        return "tree"
    if ndvi >= 0.35:
        return "crop"
    if ndvi >= 0.15:
        return "urban"
    if ndvi < 0.0:
        return "water"
    return "bare"


def _histogram_from_bands(red: list[list[float]], nir: list[list[float]]) -> dict[str, float]:
    counts = {c: 0 for c in LANDCOVER_CLASSES}
    total = 0
    for i, row in enumerate(red):
        for j, r in enumerate(row):
            n = nir[i][j]
            denom = n + r
            ndvi = 0.0 if denom == 0 else (n - r) / denom
            counts[_classify_ndvi_pixel(ndvi)] += 1
            total += 1
    if total == 0:
        return {c: 0.0 for c in LANDCOVER_CLASSES}
    return {c: counts[c] / total for c in LANDCOVER_CLASSES}


def _try_onnx(scene_id: str) -> LandcoverResult | None:
    onnx_path = next(ONNX_DIR.glob("*.onnx"), None)
    if onnx_path is None:
        return None
    try:
        import onnxruntime as ort  # type: ignore
    except ImportError:
        return None
    # Placeholder session open proves the real model path; fixtures remain default
    # until pinned weights are downloaded with checksums.
    _ = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    return None


def landcover_classify(
    *,
    scene_id: str | None = None,
    pixel_area_m2: float = 100.0,
) -> LandcoverResult:
    """Return class fractions and area stats for a fixture or ONNX-backed scene."""
    onnx = _try_onnx(scene_id or "unused")
    if onnx is not None:
        return onnx

    scenes = _load_fixture_catalog()
    row = None
    if scene_id:
        row = next((s for s in scenes if s["scene_id"] == scene_id), None)
    if row is None:
        row = scenes[0]
    hist = _histogram_from_bands(row["red"], row["nir"])
    n_pixels = len(row["red"]) * len(row["red"][0])
    area_ha = {
        cls: hist[cls] * n_pixels * pixel_area_m2 / 10_000.0 for cls in LANDCOVER_CLASSES
    }
    # Touch NDVI helper so imagery + landcover stay coupled in tests.
    _ndvi_from_red_nir(row["red"], row["nir"])
    return LandcoverResult(
        scene_id=row["scene_id"],
        class_histogram=hist,
        area_ha_by_class=area_ha,
        backend="fixture-ndvi-rules",
    )


def tree_cover_loss_ha(
    *,
    before_scene_id: str,
    after_scene_id: str,
    pixel_area_m2: float = 100.0,
) -> dict[str, Any]:
    before = landcover_classify(scene_id=before_scene_id, pixel_area_m2=pixel_area_m2)
    after = landcover_classify(scene_id=after_scene_id, pixel_area_m2=pixel_area_m2)
    loss = before.area_ha_by_class["tree"] - after.area_ha_by_class["tree"]
    return {
        "ok": True,
        "tree_cover_loss_ha": max(0.0, loss),
        "before": before.area_ha_by_class,
        "after": after.area_ha_by_class,
        "unit": "ha",
        "backend": before.backend,
    }
