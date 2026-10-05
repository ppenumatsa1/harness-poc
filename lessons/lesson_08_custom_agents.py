"""Lesson 8: custom agents (specialist sub-agents).

A custom agent = name + description + prompt + its own tool list (+ optional model).
  1. The main agent reads each agent's description and decides to delegate (via the `task` tool).
  2. The runtime runs the sub-agent in its OWN context, with only its tools.
  3. Sub-agent events stream into the SAME session (envelope `agent_id` is set).
  4. The sub-agent's answer goes back to the main agent, which writes the final reply.

Scenario: the main agent coordinates two specialists for Order 1000.
  - payment-analyst : order + payment tools (small, fast model)
  - log-analyst     : log tool only
The main agent cannot call business tools itself, so it must delegate.

Run: uv run python lessons/lesson_08_custom_agents.py
"""

import asyncio

from copilot import CopilotClient
from copilot.generated.rpc import PermissionDecisionReject
from copilot.session_events import (
    SubagentCompletedData,
    SubagentFailedData,
    SubagentStartedData,
    ToolExecutionStartData,
)
from lesson_07_custom_tools import get_logs, get_order, get_payment  # reuse Lesson 7 tools

PROMPT = (
    "Checkout failed for order 1000. Ask payment-analyst and log-analyst (in parallel) "
    "for their findings, then combine them into: ROOT CAUSE: <one line> and EVIDENCE: <2 bullets>."
)

AGENTS = [
    {
        "name": "payment-analyst",
        "display_name": "Payment Analyst",
        # The description is how the main agent picks a specialist. Be specific.
        "description": "Checks order status and payment authorization/capture state for an order id.",
        "prompt": "You analyze orders and payments. Use only your tools. Reply in 3 short lines.",
        "tools": ["get_order", "get_payment"],  # this agent sees ONLY these tools
        "model": "claude-haiku-4.5",  # cheaper model for a narrow job
    },
    {
        "name": "log-analyst",
        "display_name": "Log Analyst",
        "description": "Reads checkout, payment and inventory logs for an order id and finds the failing event.",
        "prompt": "You analyze logs. Quote the exact failing log line. Reply in 3 short lines.",
        "tools": ["get_logs"],
    },
]


def deny_all(request, invocation):
    # Business tools skip permission (read-only). Everything else is denied.
    return PermissionDecisionReject(feedback="Not allowed in Lesson 8.")


async def run() -> None:
    async with CopilotClient() as client:
        async with await client.create_session(
            model="auto",
            tools=[get_order, get_payment, get_logs],
            custom_agents=AGENTS,
            # Main agent: only `task` (delegate). Business tools stay usable by sub-agents.
            available_tools=["task", "get_order", "get_payment", "get_logs"],
            default_agent={"excluded_tools": ["get_order", "get_payment", "get_logs"]},
            on_permission_request=deny_all,
        ) as session:
            names: dict[str, str] = {}  # envelope agent_id -> agent name
            finished: set[str] = set()  # completed can be re-emitted; report each sub-agent once

            def on_event(event) -> None:
                match event.data:
                    case SubagentStartedData() as d:
                        names[event.agent_id] = d.agent_name  # started carries the sub-agent's id
                        print(f"  [main] -> start {d.agent_name} (model={d.model})")
                    case SubagentCompletedData() as d if d.tool_call_id not in finished:
                        finished.add(d.tool_call_id)
                        secs = d.duration.total_seconds() if d.duration else 0
                        print(f"  [main] <- done  {d.agent_name} model={d.model} {secs:.1f}s")
                    case SubagentFailedData() as d:
                        print(f"  [main] <- FAIL  {d.agent_name}: {d.error}")
                    case ToolExecutionStartData() as d:
                        who = names.get(event.agent_id, "main") if event.agent_id else "main"
                        print(f"  [{who}] call {d.tool_name}({d.arguments if d.tool_name != 'task' else '...'})")

            unsubscribe = session.on(on_event)
            print("\n=== Agent run ([who] = which agent emitted the event) ===")
            reply = await session.send_and_wait(PROMPT, timeout=300)
            unsubscribe()
            if reply is None:
                raise RuntimeError("Turn completed without an assistant response.")
            print("\n=== Main agent final reply ===\n" + reply.data.content)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
