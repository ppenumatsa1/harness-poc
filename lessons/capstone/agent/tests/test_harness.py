"""Offline harness tests: per-conversation lock, Finding fact checks, session cleanup (no model, no DB)."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app import harness
from app.hooks import Conversation
from app.tools import Finding

FINDING = dict(
    order_id="1000", failure_class="RESERVATION_EXPIRED", first_failure_log="x", root_cause="y",
    evidence=["z"], proposed_fix="retry", fix_id=1, confidence=0.9,
)


async def collect(gen):
    return [e async for e in gen]


def test_busy_conversation_rejects_decision_without_touching_db(monkeypatch):
    writes = []
    monkeypatch.setattr(harness.db, "write", lambda *a, **k: writes.append(a))
    h = harness.Harness()

    async def scenario():
        lock = h._lock("case-1")
        await lock.acquire()
        return await collect(h.decide("case-1", 1, True, ""))

    events = asyncio.run(scenario())
    assert events == [{"type": "error", "message": "a turn is already running for this conversation"}]
    assert writes == []


def test_busy_conversation_does_not_reset_running_turn_state():
    h = harness.Harness()
    conv = h.conversation("case-1", "1000")
    conv.proposed_fix, conv.stop_blocks = True, 1

    async def scenario():
        await h._lock("case-1").acquire()
        return await collect(h.investigate("case-1", "1000"))

    assert asyncio.run(scenario())[0]["type"] == "error"
    assert (conv.proposed_fix, conv.stop_blocks) == (True, 1)


def test_finding_fact_checks(monkeypatch):
    monkeypatch.setattr(harness, "fixes_for", lambda _cid: [{"id": 1}])
    conv = Conversation("case-1", "1000")
    check = harness.Harness._check_finding
    assert check(conv, Finding(**FINDING)) == []
    assert len(check(conv, Finding(**FINDING | {"order_id": "1001", "fix_id": 9}))) == 2
    assert check(conv, Finding(**FINDING | {"fix_id": None})) == ["a failure was found but no fix was proposed"]
    assert check(conv, Finding(**FINDING | {"failure_class": "NO_FAILURE", "fix_id": None})) == []


class FakeClient:
    def __init__(self, sessions):
        self.sessions = sessions  # id -> modified_time
        self.deleted = []

    async def list_sessions(self):
        return [SimpleNamespace(session_id=k, modified_time=v) for k, v in self.sessions.items()]

    async def delete_session(self, sid):
        self.deleted.append(sid)


class FakeSession:
    disconnected = False

    async def disconnect(self):
        self.disconnected = True


def test_close_case_deletes_session_and_state():
    h = harness.Harness()
    h.client = FakeClient({})
    s = h.sessions["case-1"] = FakeSession()
    h.conversation("case-1", "1000")
    h._lock("case-1")
    asyncio.run(h.close_case("case-1", "decided"))
    assert s.disconnected and h.client.deleted == ["case-1"]
    assert "case-1" not in h.sessions and "case-1" not in h.conversations and "case-1" not in h._locks


def test_sweep_closes_only_idle_and_not_running_cases(monkeypatch):
    monkeypatch.setattr(harness.config, "SESSION_TTL_H", 24)
    now = datetime.now(timezone.utc)
    h = harness.Harness()
    h.client = FakeClient({"old": now - timedelta(hours=30), "fresh": now - timedelta(hours=1),
                           "old-busy": now - timedelta(hours=30)})

    async def scenario():
        await h._lock("old-busy").acquire()
        return await h.sweep()

    assert asyncio.run(scenario()) == 1
    assert h.client.deleted == ["old"]


def test_decision_closes_case_when_all_fixes_are_final(monkeypatch):
    h = harness.Harness()
    closed = []

    async def fake_write(*a, **k):
        return {"id": 1, "order_id": "1000"}

    async def fake_turn(conv, prompt, schema):
        yield {"type": "done"}

    async def fake_close(cid, reason):
        closed.append((cid, reason))

    monkeypatch.setattr(harness.db, "awrite", fake_write)
    monkeypatch.setattr(h, "_run_turn", fake_turn)
    monkeypatch.setattr(h, "close_case", fake_close)
    monkeypatch.setattr(harness, "fixes_for", lambda _cid: [{"id": 1, "status": "rejected"}])
    asyncio.run(collect(h.decide("case-1", 1, False, "no")))
    assert closed == [("case-1", "decided")]

    closed.clear()
    monkeypatch.setattr(harness, "fixes_for", lambda _cid: [{"id": 1, "status": "approved"}])  # apply failed
    asyncio.run(collect(h.decide("case-1", 1, True, "")))
    assert closed == []  # keep the session so the approval can be retried
