"""Lesson 7: custom tools.

A custom tool = name + description + parameter schema + a Python handler.
  1. The SDK sends name/description/schema to the runtime (the model sees them as tool definitions).
  2. The model decides to call a tool and the runtime emits external_tool.requested.
  3. The SDK runs YOUR handler in THIS process (it can call your real APIs with your identity).
  4. The SDK returns the result; the agent loop continues with it.

Scenario: investigate Order 1000 with only 3 read-only business tools + 1 gated action tool.

Run: uv run python lessons/lesson_07_custom_tools.py
"""

import asyncio

from pydantic import BaseModel, Field

from checkout_fakes import LOGS, ORDERS, PAYMENTS
from copilot import CopilotClient, define_tool
from copilot.generated.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from copilot.session_events import (
    PermissionRequestCustomTool,
    ToolExecutionCompleteData,
    ToolExecutionStartData,
)
from copilot.tools import ToolResult

PROMPT = (
    "Customer says checkout failed for order 1000. Find the root cause using the tools. "
    "Write 'ROOT CAUSE: <one line>' and, in the same reply, call propose_fix with one fix."
)


class OrderId(BaseModel):
    # The Pydantic model becomes the JSON schema the model sees. Descriptions matter.
    order_id: str = Field(description="Checkout order id, e.g. '1000'")


# Read-only tools: skip_permission=True because they cannot change anything.
@define_tool(description="Get order status, total, items, and reservation id.", skip_permission=True)
def get_order(params: OrderId) -> dict:
    # Return a dict: the SDK serializes it to JSON for the model.
    return ORDERS.get(params.order_id) or {"error": f"order {params.order_id} not found"}


@define_tool(description="Get the payment record for an order.", skip_permission=True)
def get_payment(params: OrderId) -> dict:
    payment = dict(PAYMENTS[params.order_id])
    payment["card"] = "**** " + payment["card"][-4:]  # never return raw card data to the model
    return payment


@define_tool(description="Get checkout, payment, and inventory log lines for an order.", skip_permission=True)
async def get_logs(params: OrderId) -> ToolResult:
    # Async handler + ToolResult: full control over what the model sees vs. what is logged.
    await asyncio.sleep(0.2)  # stand-in for a real log-store query
    lines = LOGS.get(params.order_id, [])
    return ToolResult(text_result_for_llm="\n".join(lines), session_log=f"fetched {len(lines)} log lines")


class Fix(BaseModel):
    order_id: str = Field(description="Order id")
    action: str = Field(description="One proposed corrective action")


# Action tool: NO skip_permission, so every call goes through the permission handler (Lesson 6).
# is_terminal=True: a successful call ends the turn (the proposal is the final step).
@define_tool(description="Submit one corrective action for human approval.", is_terminal=True)
def propose_fix(params: Fix) -> str:
    return f"Fix for order {params.order_id} queued for approval: {params.action}"


def on_permission(request, invocation):
    if isinstance(request, PermissionRequestCustomTool):
        print(f"  permission  custom-tool {request.tool_name} args={request.args}")
        return PermissionDecisionApproveOnce()
    return PermissionDecisionReject(feedback="Only custom tools are allowed.")


async def run() -> None:
    tools = [get_order, get_payment, get_logs, propose_fix]
    async with CopilotClient() as client:
        async with await client.create_session(
            model="auto",
            tools=tools,
            # Allow-list = ONLY our tools. No shell, no files, no web. Small context too (Lesson 4).
            available_tools=[t.name for t in tools],
            on_permission_request=on_permission,
        ) as session:

            def on_event(event) -> None:
                match event.data:
                    case ToolExecutionStartData() as d:
                        print(f"  call        {d.tool_name}({d.arguments})")
                    case ToolExecutionCompleteData() as d:
                        print(f"  result      success={d.success}")

            session.on(on_event)
            print("\n=== Agent run ===")
            reply = await session.send_and_wait(PROMPT, timeout=300)
            if reply is None:
                raise RuntimeError("Turn completed without an assistant response.")
            # propose_fix is terminal: the turn ended right after it, without another model call.
            print("\n=== Last assistant message (written together with the propose_fix call) ===")
            print(reply.data.content or "(empty: the model sent only the tool call)")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
