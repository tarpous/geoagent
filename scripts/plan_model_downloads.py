#!/usr/bin/env python
"""Print model download plan without fetching weights (no GPU/HF network use)."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "models.yaml"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="demo")
    args = parser.parse_args()
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    profile = data["profiles"][args.profile]
    print(f"profile={args.profile} backend={profile.get('backend')}")
    print("Planned downloads (not executed by this script):")
    for role, cfg in sorted(profile.get("roles", {}).items()):
        print(f"  - {role}: {cfg.get('model')} @{cfg.get('quant')} -> models/ (gitignored)")
    print("Use authenticated `hf` download when ready. Do not commit weight files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
