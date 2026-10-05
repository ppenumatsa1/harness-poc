"""Lesson 7: custom tools over Postgres. Lesson 12: the Finding schema.

Read tools skip permission (read-only role). propose_fix / apply_fix go through the
permission handler (Lesson 6): propose writes a 'pending' row; apply needs a human 'approved' row.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from copilot import define_tool
from copilot.tools import ToolInvocation

from . import db


class OrderId(BaseModel):
    order_id: str = Field(description="Order id, digits only, e.g. '1000'")


class Fix(BaseModel):
    order_id: str = Field(description="Order id")
    action: str = Field(description="One concrete corrective action for a human to approve")


class FixId(BaseModel):
    fix_id: int = Field(description="Id returned by propose_fix")


class Finding(BaseModel):
    # extra="forbid" -> "additionalProperties": false, required by strict (OpenAI) schemas.
    model_config = ConfigDict(extra="forbid")
    order_id: str
    failure_class: Literal["RESERVATION_EXPIRED", "CARD_DECLINED", "FRAUD_HOLD", "NO_FAILURE", "OTHER"]
    first_failure_log: str = Field(description="The first failing log line, quoted exactly")
    root_cause: str = Field(description="One sentence")
    evidence: list[str] = Field(description="2-4 short facts with ids or timestamps")
    proposed_fix: str = Field(description="The action sent to propose_fix, or 'none'")
    fix_id: int | None = Field(description="Id returned by propose_fix, or null")
    confidence: float = Field(ge=0, le=1)


@define_tool(description="Get an order: status, total, items, reservation id.", skip_permission=True)
def get_order(params: OrderId) -> dict:
    row = db.query_one(
        "SELECT order_id, status, total_cents, currency, items, reservation_id, created_at "
        "FROM orders WHERE order_id = %s",
        (params.order_id,),
    )
    return row or {"error": f"order {params.order_id} not found"}


@define_tool(description="Get the payment record for an order (status, amount, decline code).", skip_permission=True)
def get_payment(params: OrderId) -> dict:
    # Returns the raw card number on purpose: the post-tool hook (hooks.py) redacts it.
    row = db.query_one(
        "SELECT payment_id, order_id, status, card_number, amount_cents, decline_code "
        "FROM payments WHERE order_id = %s",
        (params.order_id,),
    )
    return row or {"error": f"no payment for order {params.order_id}"}


@define_tool(description="Get the inventory reservation for an order (ttl, status).", skip_permission=True)
def get_inventory(params: OrderId) -> dict:
    row = db.query_one(
        "SELECT reservation_id, order_id, sku, qty, ttl_seconds, status, created_at "
        "FROM inventory_reservations WHERE order_id = %s",
        (params.order_id,),
    )
    return row or {"error": f"no reservation for order {params.order_id}"}


@define_tool(description="Submit ONE corrective action for human approval. Returns a fix_id. Never applies it.")
def propose_fix(params: Fix, invocation: ToolInvocation) -> dict:
    row = db.write(
        "INSERT INTO fixes (order_id, conversation_id, action) VALUES (%s, %s, %s) RETURNING id, status",
        (params.order_id, invocation.session_id, params.action),
    )
    return {"fix_id": row["id"], "status": row["status"], "note": "Waiting for a human decision."}


@define_tool(description="Apply a fix that a human has APPROVED. Fails for pending or rejected fixes.")
def apply_fix(params: FixId, invocation: ToolInvocation) -> dict:
    row = db.write(
        "UPDATE fixes SET status = 'applied' WHERE id = %s AND conversation_id = %s AND status = 'approved' "
        "RETURNING id, order_id, action, status",
        (params.fix_id, invocation.session_id),
    )
    return row or {"error": f"fix {params.fix_id} is not approved for this conversation"}


READ_TOOLS = [get_order, get_payment, get_inventory]
ACTION_TOOLS = [propose_fix, apply_fix]
ALL_TOOLS = READ_TOOLS + ACTION_TOOLS
