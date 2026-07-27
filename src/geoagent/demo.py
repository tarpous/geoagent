"""Hero demo entrypoint.

M0 dry-run validates locked config, fixture paths, golden seed emission, and a
sample FinalAnswer without calling LLM backends or live geospatial services.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from evals.factory.seed import DEFAULT_OUT, build_seed_items, write_jsonl
from geoagent.schemas import Citation, FinalAnswer, Quantity
from geoagent.swarm import run_swarm

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "models.yaml"
FIXTURE_MARKER = ROOT / "data" / "fixtures" / "README.md"
CORPUS_MANIFEST = ROOT / "data" / "corpus_manifest.csv"
HERO_QUESTION = (
    "How much tree cover was lost within 2 km of the new ring road since 2023?"
)


def _sample_final_answer() -> FinalAnswer:
    return FinalAnswer(
        trace_id="01DEMO00000000000000000000",
        status="answered",
        answer_md=(
            "Dry-run placeholder: live tree-cover loss will be computed once "
            "imagery and land-cover tools are wired."
        ),
        numbers=[
            Quantity(
                name="tree_cover_loss_placeholder",
                value=0.0,
                unit="ha",
                source_tool="landcover_classify",
            )
        ],
        citations=[
            Citation(
                doc_id="attica-env-plan-sample",
                chunk_id="fixture",
                quote="Placeholder citation for M0 dry-run validation.",
            )
        ],
        warnings=["dry-run: no live tools executed"],
        model_roster={"demo": "fixtures@m0"},
    )


def run_demo(*, dry_run: bool = False) -> int:
    if not dry_run:
        answer = run_swarm(HERO_QUESTION)
        summary = {
            "mode": "live-swarm",
            "question": HERO_QUESTION,
            "status": answer.status,
            "trace_id": answer.trace_id,
            "numbers": [n.model_dump() for n in answer.numbers],
            "citations": len(answer.citations),
            "map_artifact": str(answer.map_artifact) if answer.map_artifact else None,
            "warnings": answer.warnings,
        }
        print(json.dumps(summary, indent=2))
        return 0 if answer.status in {"answered", "degraded"} else 1

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
    answer = _sample_final_answer()
    # Also exercise the deterministic swarm on fixtures during dry-run.
    live = run_swarm(HERO_QUESTION)

    summary = {
        "mode": "dry-run",
        "question": HERO_QUESTION,
        "profile": profile_name,
        "backend": profile.get("backend"),
        "aois": aois,
        "roles": sorted(profile.get("roles", {}).keys()),
        "golden_seed": {"path": str(DEFAULT_OUT.relative_to(ROOT)), "count": len(items)},
        "final_answer_status": answer.status,
        "swarm_status": live.status,
        "swarm_tree_cover_loss_ha": next(
            (n.value for n in live.numbers if n.name == "tree_cover_loss"), None
        ),
        "status": "ok",
    }
    print(json.dumps(summary, indent=2))
    print("Demo dry-run passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="geoagent hero demo")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return run_demo(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
