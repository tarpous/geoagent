"""Hero demo entrypoint.

M0 dry-run validates locked config, fixture paths, and package wiring without
calling LLM backends or live geospatial services.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "models.yaml"
FIXTURE_MARKER = ROOT / "data" / "fixtures" / "README.md"
CORPUS_MANIFEST = ROOT / "data" / "corpus_manifest.csv"
HERO_QUESTION = (
    "How much tree cover was lost within 2 km of the new ring road since 2023?"
)


def run_demo(*, dry_run: bool = False) -> int:
    if not dry_run:
        print("Live demo is not available until later milestones. Use --dry-run for M0.")
        return 2

    if not CONFIG_PATH.is_file():
        print(f"Missing model config: {CONFIG_PATH}")
        return 1
    if not CORPUS_MANIFEST.is_file():
        print(f"Missing corpus manifest: {CORPUS_MANIFEST}")
        return 1
    if not FIXTURE_MARKER.is_file():
        print(f"Missing fixture marker: {FIXTURE_MARKER}")
        return 1

    with CONFIG_PATH.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    profile_name = config.get("default_profile", "demo")
    profile = config["profiles"][profile_name]
    aois = config.get("aois", {}).get("demo", [])

    summary = {
        "mode": "dry-run",
        "question": HERO_QUESTION,
        "profile": profile_name,
        "backend": profile.get("backend"),
        "aois": aois,
        "roles": sorted(profile.get("roles", {}).keys()),
        "status": "ok",
    }
    print(json.dumps(summary, indent=2))
    print("Demo dry-run passed.")
    return 0


def main() -> int:
    return run_demo(dry_run=True)


if __name__ == "__main__":
    raise SystemExit(main())
