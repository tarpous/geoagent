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
        help="Validate fixtures/config and run deterministic swarm",
    )

    tui = sub.add_parser("tui", help="Launch the terminal client")
    tui.add_argument("--base-url", default="")
    tui.add_argument("--once", default="")

    api = sub.add_parser("api", help="Launch the FastAPI session API + web UI")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8088)

    sub.add_parser("mcp", help="Launch the MCP server (stdio)")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    if args.command == "demo":
        from geoagent.demo import run_demo

        return run_demo(dry_run=args.dry_run)
    if args.command == "tui":
        from geoagent.tui.app import main as tui_main

        return tui_main(
            ["--base-url", args.base_url, "--once", args.once]
            if args.base_url or args.once
            else (["--once", args.once] if args.once else None)
        )
    if args.command == "api":
        import uvicorn

        from geoagent.api.app import app

        uvicorn.run(app, host=args.host, port=args.port)
        return 0
    if args.command == "mcp":
        from geoagent.mcp_server.server import main as mcp_main

        mcp_main()
        return 0
    print(f"Command '{args.command}' is not implemented yet.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
