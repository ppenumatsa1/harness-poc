"""Agent service: HTTP + SSE in front of the Copilot SDK harness.

  GET  /health    runtime + database check
  POST /invoke    {conversation_id, order_id}               -> SSE events (investigation turn)
  POST /decision  {conversation_id, fix_id, approve, note}  -> SSE events (follow-up turn)
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import db, telemetry
from .harness import Harness

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
harness = Harness()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await harness.start()
    yield
    await harness.stop()


app = FastAPI(title="checkout-investigator agent", lifespan=lifespan)
telemetry.setup(app)


class InvokeRequest(BaseModel):
    conversation_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{6,64}$")
    order_id: str = Field(pattern=r"^\d{1,10}$")


class DecisionRequest(BaseModel):
    conversation_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{6,64}$")
    fix_id: int
    approve: bool
    note: str = Field(default="", max_length=500)


def sse(events) -> StreamingResponse:
    async def body():
        async for event in events:
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(body(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/health")
async def health():
    try:
        db.query_one("SELECT 1 AS ok")
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    try:
        runtime = (await harness.client.ping("health")).message.endswith("health")  # replies "pong: health"
    except Exception:  # noqa: BLE001
        runtime = False
    return {"status": "ok" if db_ok and runtime else "degraded", "db": db_ok, "runtime": runtime}


@app.post("/invoke")
async def invoke(req: InvokeRequest):
    if db.query_one("SELECT 1 AS ok FROM orders WHERE order_id = %s", (req.order_id,)) is None:
        raise HTTPException(404, f"order {req.order_id} not found")
    return sse(harness.investigate(req.conversation_id, req.order_id))


@app.post("/decision")
async def decision(req: DecisionRequest):
    return sse(harness.decide(req.conversation_id, req.fix_id, req.approve, req.note))
