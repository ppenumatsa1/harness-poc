"""Lesson 3: events + streaming.

Everything the runtime does arrives as a session event (JSON-RPC notification `session.event`).
  A. streaming    (streaming=True -> many assistant.message_delta events, then assistant.message)
  B. timeline     (one turn with a read tool: user.message -> turn_start -> tool.* -> message -> idle)

Flow inside one turn:
  1. App calls send()                  (returns at once with a message id)
  2. Runtime emits events as it works  (SDK calls every handler registered with session.on)
  3. Runtime emits session.idle        (turn is over; send_and_wait() returns here)

Run: uv run python lessons/lesson_03_streaming_events.py
"""

import asyncio
import time
from collections import Counter
from pathlib import Path

from copilot import CopilotClient
from copilot.generated.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from copilot.session_events import (
    AssistantMessageDeltaData,
    AssistantUsageData,
    PermissionRequestRead,
    SessionErrorData,
    SessionIdleData,
    ToolExecutionCompleteData,
    ToolExecutionStartData,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
STREAM_PROMPT = "In 4 short numbered lines, explain what an agent loop is. Do not use tools."
TOOL_PROMPT = "Read pyproject.toml in the current directory and tell me the project name. One line."

# The events that tell the story of one turn. The runtime also emits many others
# (MCP status, usage info, telemetry). Part B counts those but does not print them.
CORE_EVENTS = {
    "user.message",
    "assistant.turn_start",
    "assistant.message",
    "tool.execution_start",
    "permission.requested",
    "permission.completed",
    "tool.execution_complete",
    "assistant.turn_end",
    "assistant.usage",
    "session.error",
    "session.idle",
}


def read_only(request, invocation):
    # Permission handler (Lesson 6 goes deeper): allow file reads, reject everything else.
    if isinstance(request, PermissionRequestRead):
        return PermissionDecisionApproveOnce()
    return PermissionDecisionReject(feedback="Lesson 3 allows read-only tools.")


async def part_a_streaming(client: CopilotClient) -> None:
    print("\n=== A. Streaming: print tokens as they arrive ===")
    # streaming=True asks the runtime to emit assistant.message_delta events.
    async with await client.create_session(
        model="auto", streaming=True, on_permission_request=read_only
    ) as session:
        deltas = 0

        def on_event(event) -> None:
            nonlocal deltas
            # Match on the typed payload. Each delta holds a small piece of text.
            if isinstance(event.data, AssistantMessageDeltaData):
                deltas += 1
                print(event.data.delta_content, end="", flush=True)

        unsubscribe = session.on(on_event)  # returns a function that removes the handler
        reply = await session.send_and_wait(STREAM_PROMPT)
        unsubscribe()

        if reply is None:
            raise RuntimeError("Streaming turn completed without an assistant response.")
        # The final assistant.message still arrives with the full text.
        print(f"\n--- {deltas} delta events; final message has {len(reply.data.content)} chars")


async def part_b_timeline(client: CopilotClient) -> None:
    print("\n=== B. Timeline: every event in one turn that uses a tool ===")
    async with await client.create_session(
        model="auto", working_directory=str(PROJECT_DIR), on_permission_request=read_only
    ) as session:
        counts: Counter[str] = Counter()
        start = time.perf_counter()
        done = asyncio.Event()

        def on_event(event) -> None:
            kind = event.type.value  # e.g. "tool.execution_start"
            counts[kind] += 1
            if kind not in CORE_EVENTS:
                return
            ms = int((time.perf_counter() - start) * 1000)
            detail = ""
            match event.data:
                case ToolExecutionStartData() as d:
                    detail = f"tool={d.tool_name}"
                case ToolExecutionCompleteData() as d:
                    detail = f"success={d.success}"
                case AssistantUsageData() as d:
                    detail = f"model={d.model} in={d.input_tokens} out={d.output_tokens}"
                case SessionErrorData() as d:
                    detail = f"error={d.message}"
                case SessionIdleData():
                    done.set()  # same signal send_and_wait() waits for
            # Ephemeral events are not saved to session history (e.g. deltas, progress).
            flag = " (ephemeral)" if event.ephemeral else ""
            print(f"  +{ms:>6} ms  {kind:<32}{detail}{flag}")

        unsubscribe = session.on(on_event)

        # send() is fire-and-forget: it returns a message id before the turn finishes.
        message_id = await session.send(TOOL_PROMPT)
        print(f"  send() returned at once: message_id={message_id}")
        await asyncio.wait_for(done.wait(), timeout=120)
        unsubscribe()

        # History: get_events() replays what was stored for this session.
        history = await session.get_events()
        core = sum(n for k, n in counts.items() if k in CORE_EVENTS)
        print(f"\n--- live events: {sum(counts.values())} total, {core} core (printed above)")
        print(f"--- stored in history: {len(history)} (ephemeral events are not stored)")
        print(f"--- agent loop iterations (assistant.turn_start): {counts['assistant.turn_start']}")


async def run() -> None:
    async with CopilotClient() as client:
        await part_a_streaming(client)
        await part_b_timeline(client)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
