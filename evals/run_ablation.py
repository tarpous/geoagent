"""Swarm vs single-agent ablation runner."""

from __future__ import annotations

import json
import time
from pathlib import Path

from geoagent.baseline import run_single_agent
from geoagent.swarm import run_swarm_with_trace

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "results" / "ablation_swarm_vs_single.json"

QUESTIONS = [
    "How much tree cover was lost within 2 km of the new ring road since 2023?",
    "What is mean NDVI within 2 km of the ring road since 2023?",
    "Which Attica planning docs mention flood-prone agricultural land?",
    "Count vehicles visible on a cached Attica tile.",
]


def _score(answer) -> float:
    score = 0.0
    if answer.status in {"answered", "degraded"}:
        score += 0.5
    if answer.numbers:
        score += 0.2
    if answer.citations:
        score += 0.2
    if answer.map_artifact:
        score += 0.1
    return score


def run_ablation(questions: list[str] | None = None) -> dict:
    questions = questions or QUESTIONS
    rows = []
    for q in questions:
        t0 = time.perf_counter()
        swarm_answer, trace = run_swarm_with_trace(q)
        swarm_s = time.perf_counter() - t0
        t1 = time.perf_counter()
        single_answer = run_single_agent(q)
        single_s = time.perf_counter() - t1
        rows.append(
            {
                "question": q,
                "swarm": {
                    "status": swarm_answer.status,
                    "score": _score(swarm_answer),
                    "latency_s": swarm_s,
                    "tool_call_parse_rate": trace.tool_call_parse_rate,
                    "handoffs": len(trace.handoffs),
                },
                "single": {
                    "status": single_answer.status,
                    "score": _score(single_answer),
                    "latency_s": single_s,
                    "handoffs": 0,
                },
            }
        )

    swarm_mean = sum(r["swarm"]["score"] for r in rows) / len(rows)
    single_mean = sum(r["single"]["score"] for r in rows) / len(rows)
    report = {
        "n": len(rows),
        "swarm_mean_score": swarm_mean,
        "single_mean_score": single_mean,
        "delta_swarm_minus_single": swarm_mean - single_mean,
        "backend_note": "Deterministic tool path; llama.cpp vs vLLM tok/s table filled when servers are up.",
        "llamacpp_vs_vllm": {
            "status": "pending_servers",
            "llamacpp_tok_s": None,
            "vllm_tok_s": None,
        },
        "rows": rows,
    }
    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = ROOT / "results" / "ablation_swarm_vs_single.md"
    md.write_text(
        "\n".join(
            [
                "# Swarm vs single-agent ablation",
                "",
                f"| Mode | mean score |",
                f"|---|---|",
                f"| swarm | {swarm_mean:.3f} |",
                f"| single | {single_mean:.3f} |",
                f"| delta (swarm - single) | {swarm_mean - single_mean:.3f} |",
                "",
                "llama.cpp vs vLLM latency/tok-s: pending host GPU servers.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main() -> int:
    report = run_ablation()
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "n",
                    "swarm_mean_score",
                    "single_mean_score",
                    "delta_swarm_minus_single",
                    "llamacpp_vs_vllm",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
