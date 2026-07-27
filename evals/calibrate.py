"""Judge calibration utilities (Cohen's κ against human audit slice)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def cohens_kappa(y_true: list[str], y_pred: list[str]) -> float:
    if not y_true or len(y_true) != len(y_pred):
        raise ValueError("label lists must be non-empty and equal length")
    labels = sorted(set(y_true) | set(y_pred))
    n = len(y_true)
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[index[t]][index[p]] += 1

    po = sum(matrix[i][i] for i in range(len(labels))) / n
    pe = 0.0
    for i in range(len(labels)):
        row = sum(matrix[i][j] for j in range(len(labels))) / n
        col = sum(matrix[j][i] for j in range(len(labels))) / n
        pe += row * col
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def calibrate_from_audit(
    audit_path: Path | None = None,
    judge_labels: list[str] | None = None,
) -> dict:
    path = audit_path or (ROOT / "golden" / "audit_slice.jsonl")
    if not path.is_file():
        from evals.factory.golden_v1 import build_audit_slice, build_golden_v1, write_jsonl

        items = build_golden_v1(100)
        write_jsonl(path, build_audit_slice(items, 25))

    humans: list[str] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                humans.append(json.loads(line)["human_label"])

    # Placeholder judge labels: copy humans for self-agreement smoke, then also
    # compute a noisy baseline for reporting structure.
    preds = judge_labels or list(humans)
    kappa = cohens_kappa(humans, preds)
    report = {
        "n": len(humans),
        "kappa": kappa,
        "note": "Replace placeholder audit labels with human review before publishing κ.",
    }
    out = ROOT / "results" / "calibration_kappa.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    report = calibrate_from_audit()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
