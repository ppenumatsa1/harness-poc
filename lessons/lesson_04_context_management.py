"""Lesson 4: context + state.

What does the model actually see? Where does state live?
  A. context window   (each model call = system prompt + tool definitions + conversation)
  B. shrink context   (fewer tools + a focused system message = fewer tokens per call)
  C. compaction       (summarize old turns to free space; facts must survive)
  D. workspace state  (plan.md + files in the session folder; durable, outside the context)

Run: uv run python lessons/lesson_04_context_management.py
"""

import asyncio

from copilot import CopilotClient
from copilot.generated.rpc import (
    PermissionDecisionReject,
    PlanUpdateRequest,
    SessionHistoryCompactRequest,
    WorkspacesCreateFileRequest,
)
from copilot.session_events import SessionUsageInfoData

CASE_FACTS = [
    "Case 1000 fact 1: order total is 84.20 USD.",
    "Case 1000 fact 2: payment status is AUTHORIZED, not CAPTURED.",
    "Case 1000 fact 3: inventory reservation expired at 10:02 UTC.",
]
RECALL_PROMPT = "List the 3 case 1000 facts in one line each. Do not use tools."

# A focused system message: added at the end of the built-in prompt (mode "append").
INVESTIGATOR = {
    "mode": "append",
    "content": "You are the checkout investigator for case 1000. Answer in short lines.",
}


def deny_all(request, invocation):
    # No tools needed in this lesson. Permissions are Lesson 6.
    return PermissionDecisionReject(feedback="Lesson 4 allows no tools.")


def track_context(session) -> dict:
    # session.usage_info is emitted before each model call. It shows the context budget.
    latest: dict = {}

    def on_event(event) -> None:
        if isinstance(event.data, SessionUsageInfoData):
            d = event.data
            latest.update(
                system=d.system_tokens,
                tools=d.tool_definitions_tokens,
                conversation=d.conversation_tokens,
                total=d.current_tokens,
                limit=d.token_limit,
                messages=d.messages_length,
            )

    session.on(on_event)
    return latest


def show(label: str, ctx: dict) -> None:
    pct = 100 * ctx["total"] / ctx["limit"] if ctx.get("limit") else 0
    print(
        f"  {label:<10} system={ctx.get('system')} tools={ctx.get('tools')} "
        f"conversation={ctx.get('conversation')} total={ctx.get('total')} / {ctx.get('limit')} "
        f"({pct:.1f}%) messages={ctx.get('messages')}"
    )


async def ask(session, prompt: str) -> str:
    reply = await session.send_and_wait(prompt, timeout=120)
    if reply is None:
        raise RuntimeError("Turn completed without an assistant response.")
    return reply.data.content


async def run() -> None:
    async with CopilotClient() as client:
        # A. Default session: every built-in tool definition is sent on every model call.
        print("\n=== A. Default context ===")
        async with await client.create_session(model="auto", on_permission_request=deny_all) as s:
            ctx = track_context(s)
            await ask(s, "Reply only: ok")
            show("default", ctx)

        # B. Lean session: no tools + focused system message.
        print("\n=== B. Lean context (available_tools=[] + system_message append) ===")
        async with await client.create_session(
            model="auto",
            on_permission_request=deny_all,
            available_tools=[],  # allow-list of tool names; empty = no tools
            system_message=INVESTIGATOR,
        ) as s:
            ctx = track_context(s)

            # Each turn adds to the conversation part of the context.
            for fact in CASE_FACTS:
                await ask(s, f"Remember: {fact} Reply only: noted.")
                show("turn", ctx)

            # C. Compaction: the runtime summarizes old turns into one summary message.
            #    Infinite sessions do this automatically at 80% (background) / 95% (blocking).
            print("\n=== C. Compaction (manual: session.rpc.history.compact) ===")
            result = await s.rpc.history.compact(
                SessionHistoryCompactRequest(custom_instructions="Keep every case 1000 fact exactly.")
            )
            print(
                f"  success={result.success} messages_removed={result.messages_removed} "
                f"tokens_removed={result.tokens_removed}"
            )
            print(f"  summary starts: {(result.summary_content or '')[:160]!r}")
            answer = await ask(s, RECALL_PROMPT)
            show("after", ctx)
            print("  recall after compaction:\n    " + answer.replace("\n", "\n    "))

            # D. Workspace state: durable files in the session folder. Not in the context
            #    unless the agent reads them. Survives disconnect, compaction, and resume.
            print("\n=== D. Workspace state (plan.md + files) ===")
            await s.rpc.plan.update(
                PlanUpdateRequest(content="# Case 1000\n- [x] Collect facts\n- [ ] Get approval\n")
            )
            await s.rpc.workspaces.create_file(
                WorkspacesCreateFileRequest(path="evidence/facts.txt", content="\n".join(CASE_FACTS))
            )
            plan = await s.rpc.plan.read()
            files = await s.rpc.workspaces.list_files()
            print(f"  workspace: {s.workspace_path}")
            print(f"  plan exists={plan.exists} path={plan.path}")
            print(f"  files: {files.files}")
            lean_id = s.session_id

        await client.delete_session(lean_id)  # clean up the lesson session


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
