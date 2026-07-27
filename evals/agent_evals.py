"""Agent and handoff evaluation runners."""

from __future__ import annotations

import json
from pathlib import Path

from geoagent.swarm.graph import (
    HERO_HANDOFF_PATH,
    handoff_correctness,
    run_swarm_with_trace,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "results" / "agent_handoff_m3.json"


def evaluate_hero_handoff(
    question: str = "How much tree cover was lost within 2 km of the new ring road since 2023?",
) -> dict:
    answer, trace = run_swarm_with_trace(question)
    report = {
        "question": question,
        "status": answer.status,
        "schema_ok": trace.schema_ok,
        "tool_call_parse_rate": trace.tool_call_parse_rate,
        "handoff_path": [h["to"] for h in trace.handoffs],
        "handoff_correctness": handoff_correctness(trace, HERO_HANDOFF_PATH),
        "expected_path": HERO_HANDOFF_PATH,
        "tool_calls": len(trace.tool_calls),
        "numbers": [n.model_dump() for n in answer.numbers],
    }
    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    report = evaluate_hero_handoff()
    print(json.dumps(report, indent=2))
    ok = (
        report["schema_ok"]
        and report["tool_call_parse_rate"] >= 0.95
        and report["handoff_correctness"] >= 0.8
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
