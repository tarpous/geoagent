"""Deterministic judge for golden items (LLM judge plugs in later)."""

from __future__ import annotations

import json
from pathlib import Path

from evals.factory.schema import GoldenItem
from geoagent.baseline import run_single_agent
from geoagent.swarm import run_swarm

ROOT = Path(__file__).resolve().parent


def load_golden(path: Path) -> list[GoldenItem]:
    items = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                items.append(GoldenItem.model_validate_json(line))
    return items


def judge_item(item: GoldenItem, *, mode: str = "swarm") -> dict:
    if mode == "single":
        answer = run_single_agent(item.question)
    else:
        answer = run_swarm(item.question)

    status_ok = answer.status == item.expects_status or (
        item.expects_status == "answered" and answer.status in {"answered", "degraded"}
    )
    # Refusal items should be refused; for out-of-AOI Singapore the deterministic
    # swarm currently still answers via Attica defaults — count as fail for honesty.
    if item.expects_status == "refused":
        status_ok = answer.status == "refused"

    tools_mentioned = []
    for num in answer.numbers:
        tools_mentioned.append(num.source_tool)
    if answer.citations:
        tools_mentioned.append("docs_search")
    if answer.map_artifact:
        tools_mentioned.append("make_map")

    tool_recall = 1.0
    if item.expects_tools:
        hits = sum(1 for t in item.expects_tools if t in tools_mentioned)
        tool_recall = hits / len(item.expects_tools)

    score = 0.6 * float(status_ok) + 0.4 * tool_recall
    return {
        "id": item.id,
        "mode": mode,
        "status_ok": status_ok,
        "tool_recall": tool_recall,
        "score": score,
        "answer_status": answer.status,
    }


def run_judge(
    golden_path: Path | None = None,
    *,
    mode: str = "swarm",
    limit: int | None = 20,
) -> dict:
    path = golden_path or (ROOT / "golden" / "golden_v1.jsonl")
    if not path.is_file():
        from evals.factory.golden_v1 import build_golden_v1, write_jsonl

        items = build_golden_v1(100)
        write_jsonl(path, items)
    items = load_golden(path)
    if limit is not None:
        items = items[:limit]
    rows = [judge_item(item, mode=mode) for item in items]
    mean = sum(r["score"] for r in rows) / len(rows) if rows else 0.0
    report = {
        "mode": mode,
        "n": len(rows),
        "mean_score": mean,
        "status_pass_rate": sum(1 for r in rows if r["status_ok"]) / len(rows) if rows else 0.0,
        "rows": rows,
    }
    out = ROOT / "results" / f"judge_{mode}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    report = run_judge(mode="swarm", limit=20)
    print(json.dumps({k: report[k] for k in ("mode", "n", "mean_score", "status_pass_rate")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
