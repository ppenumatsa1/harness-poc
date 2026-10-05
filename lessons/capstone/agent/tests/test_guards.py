"""Offline tests: hooks (Lessons 6 + 13), permission routing, Finding schema (Lesson 12)."""

import asyncio

import pytest
from pydantic import ValidationError

from copilot.generated.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from copilot.session_events import PermissionRequestCustomTool, PermissionRequestMcp

from app import hooks
from app.hooks import Conversation, build_hooks, build_permission_handler, redact
from app.tools import Finding


def make_conv(**kw):
    events = []
    conv = Conversation(conversation_id="c-1", order_id="1000", emit=events.append, **kw)
    return conv, events


# --- post-tool: card redaction -------------------------------------------------

@pytest.mark.parametrize("card", ["4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111"])
def test_redact_masks_card_keeps_last4(card):
    out = redact({"payment_id": "PAY-501", "card_number": card})
    assert out == {"payment_id": "PAY-501", "card_number": "**** 1111"}


def test_redact_leaves_clean_results_alone():
    assert redact({"payment_id": "PAY-501", "amount_cents": 12999}) is None


def test_post_tool_hook_returns_modified_result():
    conv, events = make_conv()
    post = build_hooks(conv)["on_post_tool_use"]
    out = post({"toolName": "get_payment", "toolResult": {"card_number": "4111111111111111"}}, None)
    assert out == {"modifiedResult": {"card_number": "**** 1111"}}
    assert events[-1]["hook"] == "post_tool"


def test_post_tool_redacts_card_leaked_in_logs():
    conv, events = make_conv()
    post = build_hooks(conv)["on_post_tool_use"]
    logs = "10:00:03 payment-gw   auth request card=4111 1111 1111 1111 amount=84.20\n10:02:01 inventory    RES-77 EXPIRED"
    out = post({"toolName": "logs-get_logs", "toolResult": logs}, None)
    assert out["modifiedResult"] == logs.replace("4111 1111 1111 1111", "**** 1111")
    assert "logs-get_logs" in events[-1]["text"]


# --- pre-tool: scope guard ------------------------------------------------------

@pytest.mark.parametrize("order_id", ["1001", "1000; DROP TABLE orders", "", "abc"])
def test_pre_tool_denies_other_orders(order_id):
    conv, _ = make_conv()
    pre = build_hooks(conv)["on_pre_tool_use"]
    out = pre({"toolName": "get_order", "toolArgs": {"order_id": order_id}}, None)
    assert out["permissionDecision"] == "deny"


def test_pre_tool_allows_own_order_and_argless_tools():
    conv, _ = make_conv()
    pre = build_hooks(conv)["on_pre_tool_use"]
    assert pre({"toolName": "get_order", "toolArgs": {"order_id": "1000"}}, None) is None
    assert pre({"toolName": "skill", "toolArgs": {"skill": "checkout-runbook"}}, None) is None


# --- agent-stop gate ------------------------------------------------------------

def test_stop_gate_blocks_once_then_lets_go():
    conv, _ = make_conv()
    stop = build_hooks(conv)["on_agent_stop"]
    assert stop({}, None)["decision"] == "block"
    assert stop({}, None) is None


def test_stop_gate_skips_after_propose_and_on_decision_turns():
    conv, _ = make_conv(proposed_fix=True)
    assert build_hooks(conv)["on_agent_stop"]({}, None) is None
    conv, _ = make_conv(turn_kind="decision")
    assert build_hooks(conv)["on_agent_stop"]({}, None) is None


def test_stop_gate_ignores_subagent_stops_and_keeps_its_block():
    conv, _ = make_conv()
    stop = build_hooks(conv)["on_agent_stop"]
    conv.active_subagents.add("call_1")
    assert stop({}, None) is None  # a sub-agent finishing
    conv.active_subagents.clear()
    assert stop({}, None)["decision"] == "block"  # the main agent, still without propose_fix


# --- permission handler ---------------------------------------------------------

def decide(handler, request):
    # The handler is async: its DB lookup runs in a worker thread (db.aquery_one).
    return asyncio.run(handler(request, None))


def test_permission_approves_propose_fix():
    conv, _ = make_conv()
    handler = build_permission_handler(conv)
    req = PermissionRequestCustomTool(tool_call_id="t1", tool_name="propose_fix", tool_description="", args={})
    assert isinstance(decide(handler, req), PermissionDecisionApproveOnce)
    assert conv.proposed_fix is False  # only a successful result (post-tool hook) counts


def test_post_tool_marks_proposed_fix_on_success_only():
    conv, _ = make_conv()
    post = build_hooks(conv)["on_post_tool_use"]
    post({"toolName": "propose_fix", "toolResult": {"error": "db down"}}, None)
    assert conv.proposed_fix is False
    post({"toolName": "propose_fix", "toolResult": '{"fix_id": 3, "status": "pending"}'}, None)
    assert conv.proposed_fix is True


@pytest.mark.parametrize("status,expected", [("approved", PermissionDecisionApproveOnce),
                                             ("pending", PermissionDecisionReject),
                                             (None, PermissionDecisionReject)])
def test_permission_apply_fix_needs_human_approval(monkeypatch, status, expected):
    monkeypatch.setattr(hooks.db, "query_one", lambda *a, **k: {"status": status} if status else None)
    conv, _ = make_conv()
    req = PermissionRequestCustomTool(tool_call_id="t1", tool_name="apply_fix", tool_description="", args={"fix_id": 7})
    assert isinstance(decide(build_permission_handler(conv), req), expected)


def test_permission_mcp_logs_read_only_only():
    conv, _ = make_conv()
    handler = build_permission_handler(conv)
    ok = PermissionRequestMcp(server_name="logs", tool_name="get_logs", tool_title="", read_only=True, args={})
    write = PermissionRequestMcp(server_name="logs", tool_name="get_logs", tool_title="", read_only=False, args={})
    other = PermissionRequestMcp(server_name="github", tool_name="x", tool_title="", read_only=True, args={})
    assert isinstance(decide(handler, ok), PermissionDecisionApproveOnce)
    assert isinstance(decide(handler, write), PermissionDecisionReject)
    assert isinstance(decide(handler, other), PermissionDecisionReject)


# --- Finding schema -------------------------------------------------------------

FINDING = {
    "order_id": "1000", "failure_class": "RESERVATION_EXPIRED",
    "first_failure_log": "10:02:01 inventory reservation RES-77 EXPIRED",
    "root_cause": "Reservation expired before capture.", "evidence": ["RES-77 ttl 120s"],
    "proposed_fix": "Re-reserve and retry capture", "fix_id": 1, "confidence": 0.9,
}


def test_finding_valid():
    assert Finding.model_validate(FINDING).fix_id == 1


@pytest.mark.parametrize("change", [{"extra": 1}, {"failure_class": "TIMEOUT"}, {"confidence": 1.5}])
def test_finding_is_strict(change):
    with pytest.raises(ValidationError):
        Finding.model_validate(FINDING | change)


def test_finding_schema_is_strict_compatible():
    schema = Finding.model_json_schema()
    assert schema["additionalProperties"] is False
    assert "fix_id" in schema["required"]
