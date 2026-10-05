"""Offline harness tests: per-conversation lock and Finding fact checks (no model, no DB)."""

import asyncio

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
