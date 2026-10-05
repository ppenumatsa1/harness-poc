"""API tests: the agent is faked with httpx.MockTransport; no model calls."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main

AGENT_EVENTS = b'data: {"type": "turn_start"}\n\ndata: {"type": "done"}\n\n'


@pytest.fixture
def agent_calls(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, json.loads(request.content or b"{}")))
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "db": True, "runtime": True})
        body = json.loads(request.content)
        if body.get("order_id") == "4040":
            return httpx.Response(404, json={"detail": "order 4040 not found"})
        return httpx.Response(200, content=AGENT_EVENTS, headers={"content-type": "text/event-stream"})

    monkeypatch.setattr(main, "agent_client",
                        lambda: httpx.AsyncClient(base_url="http://agent", transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(main, "query", lambda *a, **k: [])
    return calls


def events(text: str) -> list[dict]:
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def test_investigate_creates_case_and_relays_stream(agent_calls):
    resp = TestClient(main.app).post("/api/investigate", json={"order_id": "1000"})
    assert resp.status_code == 200
    got = events(resp.text)
    assert got[0]["type"] == "conversation" and got[0]["conversation_id"].startswith("case-")
    assert [e["type"] for e in got[1:]] == ["turn_start", "done"]
    path, body = agent_calls[0]
    assert path == "/invoke" and body == {"conversation_id": got[0]["conversation_id"], "order_id": "1000"}


def test_agent_error_becomes_http_error(agent_calls):
    resp = TestClient(main.app).post("/api/investigate", json={"order_id": "4040"})
    assert resp.status_code == 404


@pytest.mark.parametrize("body", [{"order_id": "1000; drop"}, {"order_id": ""}, {}])
def test_investigate_validates_input(agent_calls, body):
    assert TestClient(main.app).post("/api/investigate", json=body).status_code == 422
    assert agent_calls == []


def test_decision_relays_to_agent(agent_calls):
    req = {"conversation_id": "case-abc123", "fix_id": 1, "approve": True, "note": "ok"}
    resp = TestClient(main.app).post("/api/decision", json=req)
    assert resp.status_code == 200
    assert agent_calls[0] == ("/decision", req)


def test_decision_rejects_bad_conversation_id(agent_calls):
    req = {"conversation_id": "../../etc", "fix_id": 1, "approve": True}
    assert TestClient(main.app).post("/api/decision", json=req).status_code == 422


def test_health_reports_agent(agent_calls):
    body = TestClient(main.app).get("/api/health").json()
    assert body["status"] == "ok" and body["agent"]["runtime"] is True
