"""Lesson 9: checkout logs as an MCP server (stdio). The agent harness starts it as a child process.

Tool name seen by the agent: "logs-get_logs" (<server>-<tool>).
"""

import os

import psycopg2
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

server = MCPServer("logs")
DSN = (
    f"host={os.environ.get('DB_HOST', 'db')} dbname={os.environ.get('DB_NAME', 'checkout')} "
    f"user=app_ro password={os.environ.get('APP_RO_PASSWORD', '')}"
)


@server.tool(
    description="Get checkout, payment, inventory and risk log lines for an order, oldest first.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
def get_logs(order_id: str) -> str:
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT to_char(ts AT TIME ZONE 'UTC', 'HH24:MI:SS'), service, message "
            "FROM logs WHERE order_id = %s ORDER BY ts, id",
            (order_id,),
        )
        rows = cur.fetchall()
    return "\n".join(f"{t} {svc:<12} {msg}" for t, svc, msg in rows) or f"no logs for order {order_id}"


if __name__ == "__main__":
    server.run()
