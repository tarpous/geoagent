"""ONNX object detection with a fixture backend for offline CI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ONNX_DIR = ROOT / "models" / "detect"
FIXTURE_DETECTIONS = ROOT / "data" / "fixtures" / "imagery" / "detections.json"

# Documented allowlist for the demo detector.
DETECT_LABELS = ("building", "vehicle")


@dataclass(slots=True)
class Detection:
    label: str
    score: float
    bbox_xyxy: list[float]


@dataclass(slots=True)
class DetectResult:
    scene_id: str
    detections: list[Detection]
    counts: dict[str, int]
    backend: str


def _try_onnx() -> bool:
    onnx_path = next(ONNX_DIR.glob("*.onnx"), None)
    if onnx_path is None:
        return False
    try:
        import onnxruntime as ort  # type: ignore

        _ = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        return True
    except Exception:
        return False


def detect_objects(*, scene_id: str, score_threshold: float = 0.4) -> DetectResult:
    """Return boxes/labels/counts for a scene (fixture JSON or ONNX when pinned)."""
    backend = "onnx" if _try_onnx() else "fixture"
    # Until weights are pinned, always read fixture positives for determinism.
    import json

    payload = json.loads(FIXTURE_DETECTIONS.read_text(encoding="utf-8"))
    rows = payload["scenes"].get(scene_id) or payload["scenes"]["default"]
    detections = [
        Detection(label=r["label"], score=float(r["score"]), bbox_xyxy=list(r["bbox_xyxy"]))
        for r in rows
        if r["label"] in DETECT_LABELS and float(r["score"]) >= score_threshold
    ]
    counts = {label: 0 for label in DETECT_LABELS}
    for det in detections:
        counts[det.label] += 1
    return DetectResult(
        scene_id=scene_id,
        detections=detections,
        counts=counts,
        backend=backend if backend == "fixture" else "fixture+onnx-available",
    )


def detection_summary(scene_id: str) -> dict[str, Any]:
    result = detect_objects(scene_id=scene_id)
    return {
        "ok": True,
        "scene_id": result.scene_id,
        "counts": result.counts,
        "detections": [
            {"label": d.label, "score": d.score, "bbox_xyxy": d.bbox_xyxy}
            for d in result.detections
        ],
        "backend": result.backend,
    }
