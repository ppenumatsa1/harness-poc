"""DB tests (compose `db`): tools (Lesson 7), roles, approval gate, MCP logs (Lesson 9).

Run: docker compose run --rm agent pytest
"""

import asyncio
import uuid

import psycopg2
import pytest

from copilot.tools import ToolInvocation

from app import config, db
from app.tools import apply_fix, get_inventory, get_order, get_payment, propose_fix

try:
    db.query_one("SELECT 1")
except Exception as exc:  # pragma: no cover
    pytest.skip(f"db not reachable: {exc}", allow_module_level=True)


def call(tool, args, session_id="test"):
    result = asyncio.run(tool.handler(ToolInvocation(session_id=session_id, tool_name=tool.name, arguments=args)))
    return result.text_result_for_llm


def test_read_tools_return_order_1000_facts():
    assert '"reservation_id": "RES-77"' in call(get_order, {"order_id": "1000"})
    assert '"status": "AUTHORIZED"' in call(get_payment, {"order_id": "1000"})
    assert '"status": "EXPIRED"' in call(get_inventory, {"order_id": "1000"})


def test_missing_order_is_a_soft_error():
    assert "not found" in call(get_order, {"order_id": "9999"})


def test_read_only_role_cannot_write():
    with pytest.raises(psycopg2.Error):
        db.query("INSERT INTO fixes (order_id, conversation_id, action) VALUES ('1000','x','y') RETURNING id",
                 dsn=config.DB_RO_DSN)


def test_rw_role_cannot_touch_business_tables():
    with pytest.raises(psycopg2.Error):
        db.write("UPDATE orders SET status = 'PAID' WHERE order_id = '1000' RETURNING order_id")


def test_apply_fix_only_after_human_approval():
    conv = f"test-{uuid.uuid4().hex[:8]}"
    out = call(propose_fix, {"order_id": "1000", "action": "retry capture"}, session_id=conv)
    fix_id = int(out.split('"fix_id": ')[1].split(",")[0])

    assert "not approved" in call(apply_fix, {"fix_id": fix_id}, session_id=conv)
    db.write("UPDATE fixes SET status='approved' WHERE id=%s RETURNING id", (fix_id,))
    assert "not approved" in call(apply_fix, {"fix_id": fix_id}, session_id="other-conversation")
    assert '"status": "applied"' in call(apply_fix, {"fix_id": fix_id}, session_id=conv)


def test_mcp_logs_tool_reads_first_failure():
    from app.logs_mcp_server import get_logs

    lines = get_logs("1000")
    assert "RES-77 EXPIRED" in lines
    assert get_logs("9999") == "no logs for order 9999"
