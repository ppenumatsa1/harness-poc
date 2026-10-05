"""Lesson 12: user input and structured output (what goes IN and what comes OUT).

Three ways the human and the App exchange data with the agent:
  A. ask_user          : the AGENT asks the human a question mid-turn (on_user_input_request).
  B. image input       : the customer's screenshot goes in as an attachment (blob).
  C. structured output : the final answer comes back as JSON that matches a Pydantic model.

Scenario: the Order 1000 investigation, with a human approver and a case system that stores JSON.

Run: uv run python lessons/lesson_12_user_input_and_structured_output.py
"""

import asyncio
import base64
import io

from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict, Field

from copilot import CopilotClient
from copilot.generated.rpc import PermissionDecisionReject
from lesson_07_custom_tools import get_logs, get_order, get_payment  # reuse Lesson 7 tools

TOOLS = [get_order, get_payment, get_logs]


def deny_all(request, invocation):
    return PermissionDecisionReject(feedback="Not allowed in Lesson 12.")


def session_for(client, *, extra_tools=(), **kwargs):
    names = [t.name for t in TOOLS] + list(extra_tools)
    return client.create_session(
        model="auto", tools=TOOLS, available_tools=names, on_permission_request=deny_all, **kwargs
    )


# A. The agent asks. The handler can be async: in production, push the question to the App UI and wait.
async def on_user_input(request, invocation):
    print(f"  agent asks  {request['question']}")
    print(f"  choices     {request.get('choices')}")
    answer = "Retry capture"  # simulated human
    print(f"  human says  {answer}")
    return {"answer": answer, "wasFreeform": answer not in (request.get("choices") or [])}


def screenshot_png() -> str:
    # B. A fake customer screenshot of the checkout error, as base64 PNG.
    img = Image.new("RGB", (560, 140), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 559, 34], fill=(200, 30, 30))
    draw.text((12, 10), "Checkout - Payment failed", fill="white")
    draw.text((12, 55), "Order #1000   Total: $84.20", fill="black")
    draw.text((12, 85), "Error code: RESERVATION_EXPIRED (ref PAY-501)", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class Finding(BaseModel):
    # C. The schema the final answer must follow. The App can store it without parsing prose.
    # extra="forbid" -> "additionalProperties": false, which strict (OpenAI) schemas require.
    model_config = ConfigDict(extra="forbid")
    order_id: str
    root_cause: str = Field(description="One sentence")
    evidence: list[str] = Field(description="2-3 short facts with ids/timestamps")
    proposed_fix: str
    confidence: float = Field(ge=0, le=1)


async def ask_user_part(client) -> None:
    print("\n=== A. ask_user: the agent asks the human ===")
    async with await session_for(client, extra_tools=["ask_user"], on_user_input_request=on_user_input) as s:
        reply = await s.send_and_wait(
            "Investigate order 1000. Before you recommend a fix, use ask_user to ask whether to "
            "'Retry capture' or 'Refund customer'. Then give the plan in 2 lines.",
            timeout=180,
        )
        print(f"  final       {reply.data.content.strip() if reply else '(none)'}")


async def image_part(client) -> None:
    print("\n=== B. image input: customer screenshot ===")
    attachment = {"type": "blob", "data": screenshot_png(), "mimeType": "image/png", "displayName": "checkout.png"}
    async with await session_for(client) as s:
        reply = await s.send_and_wait(
            "The customer sent this screenshot. Read the order id and error code from it, "
            "then confirm with the logs tool. Two lines.",
            attachments=[attachment],
            timeout=180,
        )
        print(f"  final       {reply.data.content.strip() if reply else '(none)'}")


async def schema_part(client) -> None:
    print("\n=== C. structured output (response_schema) ===")
    async with await session_for(client) as s:
        reply = await s.send_and_wait(
            "Investigate why checkout failed for order 1000 and report the finding.",
            response_schema=Finding,
            timeout=180,
        )
        if reply is None:
            raise RuntimeError("Turn completed without an assistant response.")
        finding = Finding.model_validate_json(reply.data.content)  # fails loudly if the shape is wrong
        print(f"  validated   {type(finding).__name__} confidence={finding.confidence}")
        print(finding.model_dump_json(indent=2))


async def run() -> None:
    async with CopilotClient() as client:
        await ask_user_part(client)
        await image_part(client)
        await schema_part(client)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
