"""Lesson 11: steering and queueing (talk to the agent WHILE it works).

The human sends more messages during a running turn:
  1. send(prompt)                  : start the investigation turn.
  2. send(text, mode="immediate")  : STEER. Inject into the CURRENT turn ("also say if charged").
  3. send(text, mode="enqueue")    : QUEUE. Run as the NEXT turn, after the current one.
  4. session.idle                  : fires ONCE, after the turn and the queue are done.

Scenario: a support engineer adds details while the Order 1000 investigation runs.

Run: uv run python lessons/lesson_11_steering_and_queueing.py
"""

import asyncio

from copilot import CopilotClient
from copilot.generated.rpc import PermissionDecisionReject
from copilot.session_events import AssistantMessageData, SessionIdleData, ToolExecutionStartData
from lesson_07_custom_tools import get_logs, get_order, get_payment  # reuse Lesson 7 tools

TOOLS = [get_order, get_payment, get_logs]


def deny_all(request, invocation):
    return PermissionDecisionReject(feedback="Not allowed in Lesson 11.")


def session_for(client, *, extra_tools=(), **kwargs):
    names = [t.name for t in TOOLS] + list(extra_tools)
    return client.create_session(
        model="auto", tools=TOOLS, available_tools=names, on_permission_request=deny_all, **kwargs
    )


async def steer_and_queue(client) -> None:
    print("\n=== steer (immediate) + queue (enqueue) while the agent works ===")
    async with await session_for(client) as s:
        idle = asyncio.Event()

        def on_event(event) -> None:
            match event.data:
                case ToolExecutionStartData() as d:
                    print(f"  call        {d.tool_name}")
                case AssistantMessageData() as d if d.content and event.agent_id is None:
                    print(f"  message     {' '.join(d.content.split())}")
                case SessionIdleData():
                    print("  idle")
                    idle.set()

        s.on(on_event)
        await s.send("Investigate why checkout failed for order 1000. Use the tools. Answer in 2 lines.")
        await s.send("Also say if the customer was charged.", mode="immediate")  # steer the CURRENT turn
        await s.send("Next: write a one-line apology to the customer.", mode="enqueue")  # run AFTER this turn
        # session.idle fires once, when the turn AND the queue are done (not once per message).
        await asyncio.wait_for(idle.wait(), 300)


async def run() -> None:
    async with CopilotClient() as client:
        await steer_and_queue(client)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
