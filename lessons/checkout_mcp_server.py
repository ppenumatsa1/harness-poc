"""Checkout API as an MCP server (stdio). Used by Lesson 9.

In production this would be the App's real API, owned by the App team.
Any MCP-capable agent (Copilot SDK, Copilot CLI, VS Code, Foundry) can then use it.

Run on its own (it waits on stdin): uv run python lessons/checkout_mcp_server.py
"""

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from checkout_fakes import LOGS, ORDERS, PAYMENTS

server = MCPServer("checkout")
READ_ONLY = ToolAnnotations(readOnlyHint=True)  # the runtime reports this as read_only in permission requests
NOTES: list[str] = []


@server.tool(description="Get order status, total, items and reservation id.", annotations=READ_ONLY)
def get_order(order_id: str) -> dict:
    return ORDERS.get(order_id) or {"error": f"order {order_id} not found"}


@server.tool(description="Get the payment record for an order (card masked).", annotations=READ_ONLY)
def get_payment(order_id: str) -> dict:
    payment = dict(PAYMENTS[order_id])
    payment["card"] = "**** " + payment["card"][-4:]  # the server masks PCI data at the source
    return payment


@server.tool(description="Get checkout, payment and inventory log lines for an order.", annotations=READ_ONLY)
def get_logs(order_id: str) -> str:
    return "\n".join(LOGS.get(order_id, []))


@server.tool(description="Add an investigation note to the support case for an order.")
def add_case_note(order_id: str, note: str) -> str:
    NOTES.append(f"{order_id}: {note}")  # a write: no readOnlyHint, so the harness should gate it
    return f"note #{len(NOTES)} saved on case for order {order_id}"


if __name__ == "__main__":
    server.run("stdio")
