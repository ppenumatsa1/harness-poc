"""Lessons 6 + 13: hooks and the permission handler, built per conversation.

Order of checks for every tool call:
  1. pre-tool hook  : scope guard (the agent may only touch ITS order)
  2. permission     : read tools skip it; propose_fix allowed; apply_fix only if a human approved
  3. tool runs
  4. post-tool hook : redact card numbers before the model sees the result
"""

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from copilot.generated.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from copilot.session_events import PermissionRequestCustomTool, PermissionRequestMcp

from . import db

CARD = re.compile(r"\b(?:\d[ -]?){9,15}(\d{4})\b")
ORDER_ID = re.compile(r"^\d{1,10}$")


@dataclass
class Conversation:
    """App state for one conversation (= one SDK session)."""

    conversation_id: str
    order_id: str
    emit: Callable[[dict], None] = lambda e: None  # set per turn: sends an event to the SSE stream
    turn_kind: str = "investigate"
    proposed_fix: bool = False
    stop_blocks: int = 0
    active_subagents: set[str] = field(default_factory=set)  # tool_call_ids of running sub-agents
    timeline: list[str] = field(default_factory=list)


def text(value) -> str:
    return json.dumps(value, default=str)


def redact(value):
    dumped = text(value)
    if not CARD.search(dumped):
        return None
    return json.loads(CARD.sub(r"**** \1", dumped))


def build_hooks(conv: Conversation) -> dict:
    def note(kind: str, text: str) -> None:
        conv.timeline.append(f"{kind}: {text}")
        conv.emit({"type": "hook", "hook": kind, "text": text})

    def pre_tool(hook_input, _ctx):
        args = hook_input.get("toolArgs") or {}
        order_id = args.get("order_id") if isinstance(args, dict) else None
        if order_id is None:
            return None
        if not ORDER_ID.match(str(order_id)) or str(order_id) != conv.order_id:
            note("pre_tool", f"DENY {hook_input['toolName']}: order {order_id!r} is outside this case")
            return {
                "permissionDecision": "deny",
                "permissionDecisionReason": f"This case is about order {conv.order_id} only.",
            }
        return None

    def post_tool(hook_input, _ctx):
        if hook_input.get("toolName") == "propose_fix" and "fix_id" in text(hook_input.get("toolResult")):
            conv.proposed_fix = True  # set on success only (a failed insert never reaches this hook)
        cleaned = redact(hook_input.get("toolResult"))
        if cleaned is None:
            return None
        note("post_tool", f"redacted card number in {hook_input['toolName']} result")
        return {"modifiedResult": cleaned}

    def on_prompt(hook_input, _ctx):
        return {
            "additionalContext": (
                f"App context: case {conv.conversation_id}, order {conv.order_id}, tenant contoso. "
                "Only investigate this order."
            )
        }

    def on_agent_stop(hook_input, _ctx):
        # Lesson 13 stop gate: an investigation of a failure must end with a proposed fix.
        if conv.turn_kind != "investigate" or conv.proposed_fix:
            return None
        # The hook input does not say WHICH agent stops. While sub-agents run, a stop is
        # most likely theirs: let them finish and keep the one block for the main agent.
        if conv.active_subagents:
            return None
        if hook_input.get("stopHookActive") or conv.stop_blocks >= 1:
            return None  # blocked once already: let it stop (no loops)
        conv.stop_blocks += 1
        note("agent_stop", "blocked: no propose_fix yet")
        return {
            "decision": "block",
            "reason": "Follow the checkout-runbook: if there is a failure, call propose_fix once before finishing.",
        }

    return {
        "on_pre_tool_use": pre_tool,
        "on_post_tool_use": post_tool,
        "on_user_prompt_submitted": on_prompt,
        "on_agent_stop": on_agent_stop,
        "on_session_start": lambda i, _: note("session_start", f"source={i.get('source')}"),
        "on_post_tool_use_failure": lambda i, _: note("tool_failure", f"{i.get('toolName')}: {i.get('error')}"),
        "on_error_occurred": lambda i, _: note("error", f"{i.get('errorContext')}: {i.get('error')}"),
        "on_session_end": lambda i, _: note("session_end", f"reason={i.get('reason')}"),
    }


def build_permission_handler(conv: Conversation):
    def on_permission(request, _invocation):
        match request:
            case PermissionRequestCustomTool(tool_name="propose_fix"):
                return PermissionDecisionApproveOnce()
            case PermissionRequestCustomTool(tool_name="apply_fix"):
                fix_id = (request.args or {}).get("fix_id")
                row = db.query_one(
                    "SELECT status FROM fixes WHERE id = %s AND conversation_id = %s",
                    (fix_id, conv.conversation_id),
                )
                if row and row["status"] == "approved":
                    return PermissionDecisionApproveOnce()
                conv.emit({"type": "hook", "hook": "permission", "text": f"REJECT apply_fix {fix_id}: not approved"})
                return PermissionDecisionReject(feedback="A human has not approved this fix.")
            case PermissionRequestMcp(server_name="logs", read_only=True):
                return PermissionDecisionApproveOnce()
        conv.emit({"type": "hook", "hook": "permission", "text": f"REJECT {request.kind}"})
        return PermissionDecisionReject(feedback=f"{request.kind} is not allowed for the checkout investigator.")

    return on_permission
