"""Checkout API: the only service the browser talks to.

  GET  /api/health                         api + db + agent
  GET  /api/orders                         orders for the picker
  GET  /api/fixes?conversation_id=...      fix rows for a case
  POST /api/investigate {order_id}         new case -> relays the agent SSE stream
  POST /api/decision {conversation_id, fix_id, approve, note} -> relays the follow-up turn

The API owns the case id (App layer). The agent owns the SDK session (Harness layer).
"""

import json
import logging
import os
import uuid
from collections.abc import AsyncIterator

import httpx
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

def _secret(name: str) -> str:
    """Password from the Compose secret file in NAME_FILE; env var NAME as a fallback."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        with open(path) as f:
            return f.read().strip()
    return os.environ.get(name, "")


AGENT_URL = os.environ.get("AGENT_URL", "http://agent:8001")
DB_DSN = (
    f"host={os.environ.get('DB_HOST', 'db')} dbname={os.environ.get('DB_NAME', 'checkout')} "
    f"user=app_ro password={_secret('APP_RO_PASSWORD')}"
)
CONVERSATION_ID = r"^[a-zA-Z0-9_-]{6,64}$"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title="checkout-investigator api")

if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    configure_azure_monitor(logger_name="checkout")
    for noisy in ("azure.core.pipeline.policies.http_logging_policy", "azure.monitor.opentelemetry.exporter"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="api/health")
    HTTPXClientInstrumentor().instrument()  # adds `traceparent` -> api and agent spans join one trace


def query(sql: str, params: tuple = ()) -> list[dict]:
    with psycopg2.connect(DB_DSN, cursor_factory=psycopg2.extras.RealDictCursor) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()} for r in cur.fetchall()]


def agent_client() -> httpx.AsyncClient:
    # No read timeout: a turn streams for minutes. Tests replace this function.
    return httpx.AsyncClient(base_url=AGENT_URL, timeout=httpx.Timeout(10.0, read=None))


class InvestigateRequest(BaseModel):
    order_id: str = Field(pattern=r"^\d{1,10}$")


class DecisionRequest(BaseModel):
    conversation_id: str = Field(pattern=CONVERSATION_ID)
    fix_id: int
    approve: bool
    note: str = Field(default="", max_length=500)


def sse_event(event: dict) -> bytes:
    return f"data: {json.dumps(event)}\n\n".encode()


async def relay(path: str, payload: dict, first: dict | None = None) -> StreamingResponse:
    """Open the agent stream BEFORE answering, so agent errors become real HTTP errors."""
    client = agent_client()
    try:
        resp = await client.send(client.build_request("POST", path, json=payload), stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(502, f"agent unreachable: {exc.__class__.__name__}") from exc
    if resp.status_code != 200:
        detail = (await resp.aread()).decode(errors="replace")[:300]
        await resp.aclose()
        await client.aclose()
        raise HTTPException(resp.status_code, detail)

    async def body() -> AsyncIterator[bytes]:
        try:
            if first:
                yield sse_event(first)
            async for chunk in resp.aiter_bytes():
                yield chunk
        except httpx.HTTPError as exc:
            yield sse_event({"type": "error", "message": f"agent stream broke: {exc.__class__.__name__}"})
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        body(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
async def health():
    try:
        query("SELECT 1 AS ok")
        db_ok = True
    except psycopg2.Error:
        db_ok = False
    try:
        async with agent_client() as client:
            agent = (await client.get("/health")).json()
    except (httpx.HTTPError, ValueError):
        agent = {"status": "down"}
    ok = db_ok and agent.get("status") == "ok"
    return {"status": "ok" if ok else "degraded", "db": db_ok, "agent": agent}


@app.get("/api/orders")
def orders():
    return query("SELECT order_id, status, total_cents, currency FROM orders ORDER BY order_id")


@app.get("/api/fixes")
def fixes(conversation_id: str):
    return query(
        "SELECT id, order_id, action, status, decision_note, created_at, decided_at "
        "FROM fixes WHERE conversation_id = %s ORDER BY id",
        (conversation_id,),
    )


@app.post("/api/investigate")
async def investigate(req: InvestigateRequest):
    conversation_id = f"case-{uuid.uuid4().hex[:12]}"
    return await relay(
        "/invoke",
        {"conversation_id": conversation_id, "order_id": req.order_id},
        first={"type": "conversation", "conversation_id": conversation_id, "order_id": req.order_id},
    )


@app.post("/api/decision")
async def decision(req: DecisionRequest):
    return await relay("/decision", req.model_dump())
