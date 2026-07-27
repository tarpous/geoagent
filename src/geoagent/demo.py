"""Hero demo entrypoint.

Runs the deterministic swarm over fixtures (no GPU/LLM required) and writes
answer/trace/map artifacts under artifacts/demo/{trace_id}/.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from evals.factory.seed import DEFAULT_OUT, build_seed_items, write_jsonl

from geoagent.swarm import run_swarm_with_trace

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "models.yaml"
FIXTURE_MARKER = ROOT / "data" / "fixtures" / "README.md"
CORPUS_MANIFEST = ROOT / "data" / "corpus_manifest.csv"
HERO_QUESTION = (
    "How much tree cover was lost within 2 km of the new ring road since 2023?"
)


def _write_artifacts(answer, trace) -> Path:
    out = ROOT / "artifacts" / "demo" / answer.trace_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "answer.md").write_text(answer.answer_md or "", encoding="utf-8")
    (out / "answer.json").write_text(
        json.dumps(answer.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    trace.write(out / "trace.json")
    return out


def run_demo(*, dry_run: bool = False) -> int:
    for required in (CONFIG_PATH, CORPUS_MANIFEST, FIXTURE_MARKER):
        if not required.is_file():
            print(f"Missing required path: {required}")
            return 1

    with CONFIG_PATH.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    profile_name = config.get("default_profile", "demo")
    profile = config["profiles"][profile_name]
    aois = config.get("aois", {}).get("demo", [])

    items = build_seed_items()
    write_jsonl(DEFAULT_OUT, items)

    answer, trace = run_swarm_with_trace(HERO_QUESTION)
    artifact_dir = _write_artifacts(answer, trace)

    summary = {
        "mode": "dry-run" if dry_run else "demo",
        "question": HERO_QUESTION,
        "profile": profile_name,
        "backend": profile.get("backend"),
        "aois": aois,
        "roles": sorted(profile.get("roles", {}).keys()),
        "golden_seed": {"path": str(DEFAULT_OUT.relative_to(ROOT)), "count": len(items)},
        "swarm_status": answer.status,
        "schema_ok": trace.schema_ok,
        "tool_call_parse_rate": trace.tool_call_parse_rate,
        "swarm_tree_cover_loss_ha": next(
            (n.value for n in answer.numbers if n.name == "tree_cover_loss"), None
        ),
        "artifacts": str(artifact_dir.relative_to(ROOT)),
        "map_artifact": str(answer.map_artifact) if answer.map_artifact else None,
        "status": "ok" if answer.status in {"answered", "degraded"} else "error",
    }
    print(json.dumps(summary, indent=2))
    if dry_run:
        print("Demo dry-run passed.")
    return 0 if summary["status"] == "ok" else 1


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="geoagent hero demo")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return run_demo(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
