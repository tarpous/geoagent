"""Eval entrypoint."""

from __future__ import annotations

import argparse
import json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="geoagent evals")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("handoff", help="M3 hero handoff eval")
    sub.add_parser("golden", help="Emit golden@v1")
    sub.add_parser("judge", help="Run deterministic judge")
    sub.add_parser("calibrate", help="Compute κ calibration report")
    sub.add_parser("ablation", help="Swarm vs single ablation")
    args = parser.parse_args(argv)

    if args.cmd == "handoff":
        from evals.agent_evals import evaluate_hero_handoff

        print(json.dumps(evaluate_hero_handoff(), indent=2))
        return 0
    if args.cmd == "golden":
        from evals.factory.golden_v1 import main as golden_main

        return golden_main([])
    if args.cmd == "judge":
        from evals.judge import main as judge_main

        return judge_main()
    if args.cmd == "calibrate":
        from evals.calibrate import main as calibrate_main

        return calibrate_main()
    if args.cmd == "ablation":
        from evals.run_ablation import main as ablation_main

        return ablation_main()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
