"""Client smoke tests for API, TUI, and MCP tool registration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from geoagent.api.app import create_app
from geoagent.mcp_server.server import mcp
from geoagent.tui.app import run_local


def test_api_ask_and_health():
    client = TestClient(create_app())
    assert client.get("/health").json()["status"] == "ok"
    page = client.get("/")
    assert page.status_code == 200
    assert "geoagent" in page.text
    res = client.post(
        "/v1/ask",
        json={"question": "How much tree cover was lost within 2 km of the new ring road since 2023?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["schema_ok"] is True
    assert data["final_answer"]["status"] in {"answered", "degraded"}
    assert data["events"]


def test_api_sse_chat():
    client = TestClient(create_app())
    with client.stream(
        "POST",
        "/v1/chat",
        json={"question": "Count vehicles visible on a cached Attica tile."},
    ) as response:
        body = "".join(response.iter_text())
    assert "event: event" in body or "event: done" in body
    assert "final_answer" in body


def test_api_out_of_aoi_refusal():
    client = TestClient(create_app())
    res = client.post(
        "/v1/ask",
        json={"question": "Measure mangrove loss near Singapore since 2020."},
    )
    assert res.status_code == 200
    answer = res.json()["final_answer"]
    assert answer["status"] == "refused"
    assert answer["refusal"]["reason_code"] == "out_of_aoi"


def test_tui_local_once():
    payload = run_local("How much tree cover was lost within 2 km of the new ring road since 2023?")
    assert payload["schema_ok"] is True
    assert payload["final_answer"]["numbers"]


def test_mcp_registers_ask_swarm_and_tools():
    tools = mcp._tool_manager.list_tools()  # noqa: SLF001 - smoke check registration
    names = {t.name for t in tools}
    assert "ask_swarm" in names
    assert "show_trace" in names
    assert "tool_docs_search" in names
    assert "tool_landcover" in names
