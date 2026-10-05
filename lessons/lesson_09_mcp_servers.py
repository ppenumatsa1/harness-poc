"""Lesson 9: MCP + integrations.

MCP (Model Context Protocol) = a standard plug for tools. Write the tools once, as a server.
  1. The session config names an MCP server: how to start it (stdio) or where it is (http).
  2. The runtime starts/connects to the server and lists its tools.
  3. The model sees the MCP tools next to built-in and custom tools.
  4. Each call goes runtime -> MCP server (not through your Python handler).
     The permission handler still sees it as kind "mcp" (with server, tool, read_only).

Scenario: the checkout App team ships its API as an MCP server (lessons/checkout_mcp_server.py).
The harness plugs it in. Reads are auto-approved; writing a case note needs a human.

Run: uv run python lessons/lesson_09_mcp_servers.py
"""

import asyncio
import sys
from pathlib import Path

from copilot import CopilotClient
from copilot.generated.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from copilot.session_events import (
    PermissionRequestMcp,
    SessionMcpServersLoadedData,
    SessionMcpServerStatusChangedData,
    ToolExecutionCompleteData,
    ToolExecutionStartData,
)

SERVER = Path(__file__).with_name("checkout_mcp_server.py")

PROMPT = (
    "Checkout failed for order 1000. Use the checkout tools to find the root cause, "
    "then add one case note with the root cause. Finish with 'ROOT CAUSE: <one line>'."
)

MCP_SERVERS = {
    "checkout": {
        "type": "stdio",
        "command": sys.executable,  # same venv python, so the server can import mcp + checkout_fakes
        "args": [str(SERVER)],
        "tools": ["*"],  # expose every tool of this server ([] = none, or list names)
        "timeout": 30_000,  # ms
    }
}


async def human_approver(what: str) -> bool:
    print(f"  human       approve {what}? -> yes (simulated)")
    return True


async def on_permission(request, invocation):
    match request:
        # Note: tools marked readOnlyHint did not reach this handler in our run (runtime auto-approved).
        # Keep the case anyway: the policy stays correct if that runtime behavior changes.
        case PermissionRequestMcp(read_only=True):
            print(f"  permission  APPROVE mcp read  {request.server_name}/{request.tool_name}")
            return PermissionDecisionApproveOnce()
        case PermissionRequestMcp():
            print(f"  permission  ASK     mcp write {request.server_name}/{request.tool_name} args={request.args}")
            if await human_approver(request.tool_name):
                return PermissionDecisionApproveOnce()
            return PermissionDecisionReject(feedback="The human declined this case note.")
    return PermissionDecisionReject(feedback="Only checkout MCP tools are allowed in Lesson 9.")


async def run() -> None:
    async with CopilotClient() as client:
        async with await client.create_session(
            model="auto",
            mcp_servers=MCP_SERVERS,
            # MCP tools are named "<server>-<tool>". Allow only ours: the user's global MCP
            # servers (from ~/.copilot) still load, but their tools stay out of the context.
            available_tools=[f"checkout-{n}" for n in ("get_order", "get_payment", "get_logs", "add_case_note")],
            on_permission_request=on_permission,
        ) as session:

            def on_event(event) -> None:
                match event.data:
                    case ToolExecutionStartData() as d:
                        print(f"  call        {d.tool_name}({d.arguments})")
                    case ToolExecutionCompleteData() as d:
                        print(f"  result      success={d.success}")
                    case SessionMcpServerStatusChangedData() as d if d.server_name == "checkout":
                        print(f"  mcp         checkout -> {d.status.value}")
                    case SessionMcpServersLoadedData() as d:
                        ours = [s for s in d.servers if s.name == "checkout"]
                        print(f"  mcp         loaded {len(d.servers)} servers; checkout={ours[0].status.value if ours else 'missing'}")

            session.on(on_event)
            print("\n=== Agent run ===")
            reply = await session.send_and_wait(PROMPT, timeout=300)
            if reply is None:
                raise RuntimeError("Turn completed without an assistant response.")
            print("\n=== Final reply ===\n" + reply.data.content)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
