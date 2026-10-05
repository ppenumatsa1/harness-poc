"""Lesson 13: skills and lifecycle hooks (+ session limits, client info).

Five ways to shape the agent WITHOUT changing the model or the tools:
  A. skills          : a SKILL.md runbook the agent loads when the task matches (skill_directories).
  B. prompt hook     : on_user_prompt_submitted adds App context (case id, tenant) to every prompt.
  C. lifecycle hooks : on_session_start / on_post_tool_use_failure / on_error_occurred / on_session_end
                       write the App's case timeline.
  D. agent-stop gate : on_agent_stop blocks "done" until the reply has a ROOT CAUSE line.
  E. limits + client : session_limits caps AI credits per case; client_info tags who is calling.

Scenario: the Order 1000 investigation, now run by a "checkout-harness" App.

Run: uv run python lessons/lesson_13_skills_and_lifecycle_hooks.py
"""

import asyncio
from pathlib import Path

from pydantic import BaseModel

from copilot import CopilotClient, define_tool
from copilot.generated.rpc import PermissionDecisionReject
from copilot.session_events import SkillInvokedData, ToolExecutionStartData
from lesson_07_custom_tools import get_logs, get_order, get_payment  # reuse Lesson 7 tools

TOOLS = [get_order, get_payment, get_logs]
SKILLS_DIR = str(Path(__file__).parent / "skills")  # parent dir; each child dir has a SKILL.md
CLIENT_INFO = {"application_name": "checkout-harness", "application_version": "0.13.0"}


def deny_all(request, invocation):
    return PermissionDecisionReject(feedback="Not allowed in Lesson 13.")


def session_for(client, *, tools=TOOLS, extra_tools=(), **kwargs):
    names = [t.name for t in tools] + list(extra_tools)
    return client.create_session(
        model="auto", tools=tools, available_tools=names, on_permission_request=deny_all, **kwargs
    )


def reply_text(reply) -> str:
    return reply.data.content.strip() if reply and reply.data.content else "(none)"


async def part_a(client) -> None:
    print("\n=== A. skills: the checkout-runbook SKILL.md ===")
    # "skill" is the built-in tool the agent uses to load a skill; it must be in available_tools.
    async with await session_for(client, extra_tools=["skill"], skill_directories=[SKILLS_DIR]) as s:
        s.on(lambda e: isinstance(e.data, SkillInvokedData) and print(f"  skill       {e.data.name} ({e.data.path})"))
        reply = await s.send_and_wait("Checkout failed for order 1000. Investigate.", timeout=180)
        print(reply_text(reply))


async def part_b(client) -> None:
    print("\n=== B. prompt hook: the App adds case context ===")

    def on_prompt(hook_input, invocation):
        print(f"  hook        user_prompt_submitted: {hook_input['prompt']!r}")
        # additionalContext is added for the model; the user's prompt stays unchanged.
        return {"additionalContext": "App context: case CASE-77, tenant contoso, customer tier GOLD."}

    async with await session_for(client, hooks={"on_user_prompt_submitted": on_prompt}) as s:
        reply = await s.send_and_wait("Which case, tenant and tier am I working on? One line.", timeout=120)
        print(f"  final       {reply_text(reply)}")


class Empty(BaseModel):
    pass


@define_tool(description="Get the refund policy for checkout failures.", skip_permission=True)
def get_refund_policy(params: Empty) -> str:
    raise ConnectionError("policy-service unreachable")  # simulated outage


async def part_c(client) -> None:
    print("\n=== C. lifecycle + error hooks: the App's case timeline ===")
    timeline: list[str] = []

    hooks = {
        "on_session_start": lambda i, _: timeline.append(f"start  source={i.get('source')}"),
        "on_post_tool_use_failure": lambda i, _: timeline.append(f"tool-failed {i['toolName']}: {i['error']}"),
        "on_error_occurred": lambda i, _: timeline.append(f"error  {i.get('errorContext')}: {i.get('error')}"),
        "on_session_end": lambda i, _: timeline.append(f"end    reason={i.get('reason')}"),
    }
    tools = TOOLS + [get_refund_policy]
    async with await session_for(client, tools=tools, hooks=hooks) as s:
        reply = await s.send_and_wait(
            "Get the refund policy for order 1000, then say in one line what it is.", timeout=120
        )
        print(f"  final       {reply_text(reply)}")
    await asyncio.sleep(1)  # session end hook arrives as the session closes
    for line in timeline:
        print(f"  timeline    {line}")


async def part_d(client) -> None:
    print("\n=== D. agent-stop gate: no ROOT CAUSE line, no finish ===")
    blocks = 0

    async def on_agent_stop(hook_input, invocation):
        nonlocal blocks
        if hook_input.get("stopHookActive") or blocks >= 2:
            return None  # already continued once due to this hook: let it stop (avoid loops)
        blocks += 1
        print(f"  hook        agent_stop #{blocks}: block, ask for ROOT CAUSE line")
        return {"decision": "block", "reason": "Finish with a line 'ROOT CAUSE: <one line>' quoting the log."}

    async with await session_for(client, hooks={"on_agent_stop": on_agent_stop}) as s:
        s.on(lambda e: isinstance(e.data, ToolExecutionStartData) and print(f"  call        {e.data.tool_name}"))
        reply = await s.send_and_wait("Look at order 1000. Reply with just the order status.", timeout=180)
        print(f"  final       {reply_text(reply)}")


async def part_e(client) -> None:
    print("\n=== E. session limits + client info ===")
    seen: list[str] = []
    async with await session_for(client, session_limits={"max_ai_credits": 100.0}) as s:
        s.on(lambda e: "limit" in e.type.value and seen.append(e.type.value))
        reply = await s.send_and_wait("Order 1000 status in 5 words.", timeout=120)
        metrics = await s.rpc.usage.get_metrics()
        print(f"  final       {reply_text(reply)}")
        print(f"  limit       max_ai_credits=100.0, used nano_aiu={metrics.total_nano_aiu}")
        print(f"  events      {seen or 'no limit events (well under the cap)'}")
        print(f"  client_info {CLIENT_INFO} (sent once at client start)")


async def run() -> None:
    async with CopilotClient(client_info=CLIENT_INFO) as client:
        await part_a(client)
        await part_b(client)
        await part_c(client)
        await part_d(client)
        await part_e(client)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
