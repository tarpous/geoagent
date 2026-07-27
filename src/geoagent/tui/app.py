"""Custom terminal client for the shared swarm session."""

from __future__ import annotations

import argparse
import json
from typing import Any

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from geoagent.swarm import run_swarm_with_trace

console = Console()


def run_local(question: str) -> dict[str, Any]:
    answer, trace = run_swarm_with_trace(question)
    return {
        "final_answer": answer.model_dump(mode="json"),
        "events": trace.events,
        "tool_call_parse_rate": trace.tool_call_parse_rate,
        "schema_ok": trace.schema_ok,
    }


def run_http(question: str, base_url: str) -> dict[str, Any]:
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=120.0) as client:
        response = client.post("/v1/ask", json={"question": question})
        response.raise_for_status()
        return response.json()


def render(payload: dict[str, Any]) -> None:
    fa = payload.get("final_answer") or {}
    console.print(Panel(Markdown(fa.get("answer_md") or "_empty_"), title=f"status={fa.get('status')}"))
    console.print(
        f"[dim]schema_ok={payload.get('schema_ok')} parse_rate={payload.get('tool_call_parse_rate')}[/dim]"
    )
    for event in payload.get("events") or []:
        agent = event.get("agent") or "-"
        console.print(f"[cyan]{event.get('type')}[/cyan] [{agent}] {json.dumps(event.get('payload') or {})}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="geoagent TUI")
    parser.add_argument("--base-url", default="", help="If set, call FastAPI instead of in-process swarm")
    parser.add_argument("--once", default="", help="Ask one question and exit")
    args = parser.parse_args(argv)

    def ask(question: str) -> None:
        payload = run_http(question, args.base_url) if args.base_url else run_local(question)
        render(payload)

    if args.once:
        ask(args.once)
        return 0

    console.print("[bold]geoagent TUI[/bold] — type a question, or /quit")
    while True:
        try:
            question = console.input("[green]>[/green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0
        if not question:
            continue
        if question in {"/quit", "/exit", "quit", "exit"}:
            return 0
        if question == "/trace":
            console.print("[dim]Trace is printed after each answer.[/dim]")
            continue
        ask(question)


if __name__ == "__main__":
    raise SystemExit(main())
