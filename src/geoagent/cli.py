"""Command-line entrypoints for geoagent."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geoagent", description="Geospatial analyst swarm")
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="Run the Attica hero demo path")
    demo.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate fixtures/config without calling LLMs or live tools",
    )

    sub.add_parser("tui", help="Launch the terminal client (not yet implemented)")
    sub.add_parser("mcp", help="Launch the MCP server (not yet implemented)")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    if args.command == "demo":
        from geoagent.demo import run_demo

        return run_demo(dry_run=args.dry_run)
    print(f"Command '{args.command}' is not implemented yet.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
