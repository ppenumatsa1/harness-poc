"""The Copilot SDK harness: one client, one SDK session per conversation.

Lesson map:
  1  CopilotClient + create_session          2  session_id = conversation id; resume_session
  3  session.on -> stream events              4  system message + infinite sessions (compaction)
  5  BYOK provider + Entra bearer token       6  permission handler + tool hooks (hooks.py)
  7  custom tools (tools.py)                  8  custom agents + task delegation
  9  MCP logs server                          10 OpenTelemetry spans
  12 response_schema=Finding                  13 skill, prompt/lifecycle hooks, stop gate, limits, client info

Session lifecycle: a case's SDK session is deleted when its fix is applied or rejected,
or by the sweeper once it is idle for SESSION_TTL_H hours (cases with no fix).
"""

import asyncio
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from azure.identity import AzureCliCredential
from opentelemetry import context as otel_context
from opentelemetry import trace

from copilot import CopilotClient

from . import config, db
from .hooks import Conversation, build_hooks, build_permission_handler
from .telemetry import tracer
from .tools import ALL_TOOLS, READ_TOOLS, Finding

log = logging.getLogger("checkout.harness")
HERE = Path(__file__).parent
LOGS_TOOL = "logs-get_logs"
READ_NAMES = [t.name for t in READ_TOOLS] + [LOGS_TOOL]

SYSTEM = {
    "mode": "append",
    "content": (
        "You are the checkout investigator for Contoso. You investigate ONE order per case. "
        "Load the checkout-runbook skill first and follow it. Delegate fact finding to the specialists. "
        "Facts must come from tools; never guess ids, times or amounts."
    ),
}

AGENTS = [
    {
        "name": "payment-analyst",
        "display_name": "Payment analyst",
        "description": "Gets order and payment facts for an order id: status, amounts, authorization, decline code.",
        "prompt": "You analyze orders and payments. Use only your tools. Reply in at most 4 short lines with ids.",
        "tools": ["get_order", "get_payment"],
    },
    {
        "name": "inventory-analyst",
        "display_name": "Inventory analyst",
        "description": "Gets the inventory reservation and the logs for an order id, and quotes the first failing log line.",
        "prompt": "You analyze reservations and logs. Quote the first failing log line exactly. At most 4 short lines.",
        "tools": ["get_inventory", LOGS_TOOL],
    },
]

MCP_SERVERS = {
    "logs": {
        "type": "stdio",
        "command": sys.executable,
        "args": ["-m", "app.logs_mcp_server"],
        "working_directory": str(HERE.parent),
        "env": {k: v for k, v in os.environ.items() if k in ("DB_HOST", "DB_NAME", "APP_RO_PASSWORD_FILE", "PATH")},
        "tools": ["*"],
        "timeout": 30_000,
    }
}


class TokenProvider:
    """Lesson 5: BYOK bearer token from your `az login` (mounted ~/.azure). Cached until 5 min before expiry."""

    def __init__(self) -> None:
        self._cred = AzureCliCredential()
        self._lock = threading.Lock()
        self._token = None

    def __call__(self, _args=None) -> str:
        with self._lock:
            if self._token is None or self._token.expires_on - time.time() < 300:
                self._token = self._cred.get_token(config.FOUNDRY_SCOPE)
            return self._token.token


class Harness:
    def __init__(self) -> None:
        self.client: CopilotClient | None = None
        self.token = TokenProvider()
        self.conversations: dict[str, Conversation] = {}
        self.sessions: dict[str, object] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._sweeper: asyncio.Task | None = None

    async def start(self) -> None:
        # use_logged_in_user=False: no GitHub identity. BYOK needs only the Foundry token.
        self.client = CopilotClient(client_info=config.CLIENT_INFO, use_logged_in_user=False)
        await self.client.start()
        self._sweeper = asyncio.create_task(self._sweep_forever())

    async def stop(self) -> None:
        if self._sweeper:
            self._sweeper.cancel()
        for s in list(self.sessions.values()):
            try:
                await s.disconnect()
            except Exception:  # noqa: BLE001 - best effort on shutdown
                pass
        if self.client:
            await self.client.stop()

    def _session_kwargs(self, conv: Conversation) -> dict:
        kwargs = dict(
            model=config.FOUNDRY_MODEL,
            provider={
                "type": "openai",
                "base_url": config.FOUNDRY_BASE_URL,
                "wire_api": "responses",
                "bearer_token_provider": self.token,
            },
            tools=ALL_TOOLS,
            available_tools=["task", "skill", "propose_fix", "apply_fix", *READ_NAMES],
            # The main agent delegates reads to the specialists (Lesson 8).
            default_agent={"excluded_tools": READ_NAMES},
            custom_agents=AGENTS,
            mcp_servers=MCP_SERVERS,
            skill_directories=[str(HERE / "skills")],
            system_message=SYSTEM,
            hooks=build_hooks(conv),
            on_permission_request=build_permission_handler(conv),
            working_directory="/tmp",
            enable_config_discovery=False,
        )
        if config.MAX_AI_CREDITS > 0:
            kwargs["session_limits"] = {"max_ai_credits": config.MAX_AI_CREDITS}
        return kwargs

    async def _session(self, conv: Conversation):
        sid = conv.conversation_id
        if sid in self.sessions:
            return self.sessions[sid]
        if await self.client.get_session_metadata(sid):  # Lesson 2: after an agent restart, resume from disk
            session = await self.client.resume_session(sid, **self._session_kwargs(conv))
        else:
            session = await self.client.create_session(
                session_id=sid,
                infinite_sessions={"enabled": True, "background_compaction_threshold": 0.8},
                **self._session_kwargs(conv),
            )
        self.sessions[sid] = session
        return session

    def conversation(self, conversation_id: str, order_id: str) -> Conversation:
        conv = self.conversations.get(conversation_id)
        if conv is None:
            conv = self.conversations[conversation_id] = Conversation(conversation_id, order_id)
        return conv

    async def investigate(self, conversation_id: str, order_id: str) -> AsyncIterator[dict]:
        lock = self._lock(conversation_id)
        if lock.locked():
            yield {"type": "error", "message": "a turn is already running for this conversation"}
            return
        async with lock:  # reset per-turn state only once we own the conversation
            conv = self.conversation(conversation_id, order_id)
            conv.turn_kind, conv.proposed_fix, conv.stop_blocks = "investigate", False, 0
            prompt = f"Checkout problem reported for order {order_id}. Investigate and report the finding."
            async for event in self._run_turn(conv, prompt, schema=Finding):
                yield event

    async def decide(self, conversation_id: str, fix_id: int, approve: bool, note: str) -> AsyncIterator[dict]:
        lock = self._lock(conversation_id)
        if lock.locked():
            yield {"type": "error", "message": "a turn is already running for this conversation"}
            return
        async with lock:  # record the decision only when its follow-up turn can run
            status = "approved" if approve else "rejected"
            # An approved-but-not-applied fix may be approved again: retries a failed follow-up turn.
            row = await db.awrite(
                "UPDATE fixes SET status = %s, decision_note = %s, decided_at = now() "
                "WHERE id = %s AND conversation_id = %s "
                "AND (status = 'pending' OR (status = 'approved' AND %s)) RETURNING id, order_id",
                (status, note[:500], fix_id, conversation_id, approve),
            )
            if row is None:
                yield {"type": "error", "message": f"fix {fix_id} is not pending in conversation {conversation_id}"}
                return
            conv = self.conversation(conversation_id, row["order_id"])
            conv.turn_kind = "decision"
            if approve:
                prompt = f"The human APPROVED fix {fix_id}. Call apply_fix with fix_id={fix_id}, then confirm in one line."
            else:
                prompt = (
                    f"The human REJECTED fix {fix_id}. Their note: {note[:500]!r}. Do not call apply_fix. "
                    "Suggest one safer next step in at most two lines."
                )
            yield {"type": "decision", "fix_id": fix_id, "status": status}
            async for event in self._run_turn(conv, prompt, schema=None):
                yield event
            fixes = await asyncio.to_thread(fixes_for, conversation_id)
            if fixes and all(f["status"] in ("applied", "rejected") for f in fixes):
                await self.close_case(conversation_id, "decided")

    async def close_case(self, conversation_id: str, reason: str) -> None:
        """Delete the SDK session (history on disk) and drop in-memory state. The fixes table keeps the record."""
        session = self.sessions.pop(conversation_id, None)
        self.conversations.pop(conversation_id, None)
        lock = self._locks.get(conversation_id)
        if lock is not None and not lock.locked():
            self._locks.pop(conversation_id, None)
        try:
            if session is not None:
                await session.disconnect()
            await self.client.delete_session(conversation_id)
            log.info("closed case %s (%s): session deleted", conversation_id, reason)
        except Exception:  # noqa: BLE001 - cleanup is best effort
            log.warning("could not delete session %s", conversation_id, exc_info=True)

    async def sweep(self) -> int:
        """Close idle cases (for example NO_FAILURE cases that never get a decision)."""
        now = datetime.now(timezone.utc)
        closed = 0
        for meta in await self.client.list_sessions():
            sid = meta.session_id
            modified = meta.modified_time if meta.modified_time.tzinfo else meta.modified_time.replace(tzinfo=timezone.utc)
            idle_h = (now - modified).total_seconds() / 3600
            lock = self._locks.get(sid)
            if idle_h >= config.SESSION_TTL_H and not (lock and lock.locked()):
                await self.close_case(sid, f"idle {idle_h:.1f}h")
                closed += 1
        return closed

    async def _sweep_forever(self) -> None:
        while True:
            try:
                await self.sweep()
            except Exception:  # noqa: BLE001
                log.warning("session sweep failed", exc_info=True)
            await asyncio.sleep(config.SWEEP_INTERVAL_S)

    def _lock(self, conversation_id: str) -> asyncio.Lock:
        return self._locks.setdefault(conversation_id, asyncio.Lock())

    @staticmethod
    def _check_finding(conv: Conversation, finding: Finding) -> list[str]:
        """Shape is checked by the schema; here we check the facts against the App's data."""
        problems = []
        if finding.order_id != conv.order_id:
            problems.append(f"order_id {finding.order_id} is not this case's order {conv.order_id}")
        own = {f["id"] for f in fixes_for(conv.conversation_id)}
        if finding.fix_id is not None and finding.fix_id not in own:
            problems.append(f"fix_id {finding.fix_id} was not proposed in this conversation")
        if finding.failure_class != "NO_FAILURE" and finding.fix_id is None:
            problems.append("a failure was found but no fix was proposed")
        return problems

    async def _run_turn(self, conv: Conversation, prompt: str, schema) -> AsyncIterator[dict]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        conv.emit = lambda e: loop.call_soon_threadsafe(queue.put_nowait, e)
        conv.active_subagents.clear()
        usage = {"input_tokens": 0, "output_tokens": 0, "model_calls": 0, "model": None}
        started = time.monotonic()
        # Explicit span + context (not start_as_current_span): this generator yields across awaits.
        turn_span = tracer.start_span(f"invoke_agent {conv.turn_kind}")
        turn_span.set_attributes({
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.name": "checkout-investigator",
            "gen_ai.conversation.id": conv.conversation_id,
            "checkout.order_id": conv.order_id,
            "checkout.turn_kind": conv.turn_kind,
        })
        turn_ctx = trace.set_span_in_context(turn_span)
        tool_spans: dict[str, trace.Span] = {}
        on_event = self._event_mapper(conv, usage, tool_spans, turn_ctx)
        unsubscribe = None
        session = None
        task = None
        try:
            session = await self._session(conv)
            unsubscribe = session.on(on_event)
            yield {"type": "turn_start", "kind": conv.turn_kind, "conversation_id": conv.conversation_id,
                   "order_id": conv.order_id, "model": config.FOUNDRY_MODEL}
            send_kwargs = {"timeout": config.TURN_TIMEOUT_S}
            if schema is not None:
                send_kwargs["response_schema"] = schema
            token = otel_context.attach(turn_ctx)  # the SDK task inherits the turn span
            try:
                task = asyncio.create_task(session.send_and_wait(prompt, **send_kwargs))
            finally:
                otel_context.detach(token)
            while not task.done() or not queue.empty():
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
            reply = task.result()
            content = reply.data.content if reply else ""
            if schema is not None:
                finding = schema.model_validate_json(content)
                yield {"type": "finding", "finding": finding.model_dump()}
                problems = await asyncio.to_thread(self._check_finding, conv, finding)
                if problems:
                    yield {"type": "error", "message": "finding failed fact checks: " + "; ".join(problems)}
            else:
                yield {"type": "message", "text": content.strip()}
        except Exception as exc:  # noqa: BLE001 - report every failure to the UI
            log.exception("turn failed")
            turn_span.record_exception(exc)
            turn_span.set_status(trace.StatusCode.ERROR, str(exc))
            yield {"type": "error", "message": f"{type(exc).__name__}: {exc}"}
        finally:
            if task and not task.done():
                # Client went away or the turn failed: cancelling the waiter does NOT stop the
                # runtime, so abort the in-flight message before the lock is released.
                log.info("turn interrupted; aborting session %s", conv.conversation_id)
                try:
                    if session is not None:
                        await asyncio.wait_for(session.abort(), timeout=10)
                except Exception:  # noqa: BLE001
                    log.warning("session abort failed", exc_info=True)
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            if unsubscribe:
                unsubscribe()
            for span in tool_spans.values():
                span.end()
            conv.emit = lambda e: None
            usage["duration_s"] = round(time.monotonic() - started, 1)
            turn_span.set_attributes({
                "gen_ai.usage.input_tokens": usage["input_tokens"],
                "gen_ai.usage.output_tokens": usage["output_tokens"],
                "checkout.model_calls": usage["model_calls"],
            })
            turn_span.end()
        while not queue.empty():
            yield queue.get_nowait()
        yield {"type": "done", "usage": usage, "fixes": await asyncio.to_thread(fixes_for, conv.conversation_id)}

    @staticmethod
    def _event_mapper(conv: Conversation, usage: dict, tool_spans: dict, turn_ctx):
        """Lesson 3: turn SDK events into small UI events (+ Lesson 10 tool spans)."""
        agent_names: dict[str, str] = {}

        def on_event(event) -> None:
            t, d = event.type.value, event.data
            if t == "tool.execution_start":
                span = tracer.start_span(f"execute_tool {d.tool_name}", context=turn_ctx)
                span.set_attributes({"gen_ai.tool.name": d.tool_name, "gen_ai.tool.call.id": d.tool_call_id})
                tool_spans[d.tool_call_id] = span
                conv.emit({
                    "type": "tool_start", "tool": d.tool_name, "call_id": d.tool_call_id,
                    "args": d.arguments if isinstance(d.arguments, (dict, str)) else None,
                    "agent": agent_names.get(d.parent_tool_call_id or "", "main"),
                })
            elif t == "tool.execution_complete":
                span = tool_spans.pop(d.tool_call_id, None)
                if span:
                    span.set_attribute("checkout.tool.success", d.success)
                    if not d.success:
                        span.set_status(trace.StatusCode.ERROR, str(d.error))
                    span.end()
                conv.emit({"type": "tool_done", "call_id": d.tool_call_id, "success": d.success,
                           "error": getattr(d.error, "message", None) if d.error else None})
            elif t == "subagent.started":
                agent_names[d.tool_call_id] = d.agent_name
                conv.active_subagents.add(d.tool_call_id)
                conv.emit({"type": "subagent", "agent": d.agent_name, "state": "started"})
            elif t in ("subagent.completed", "subagent.failed"):
                conv.active_subagents.discard(d.tool_call_id)
                if agent_names.pop(d.tool_call_id, None) is not None:  # completed can arrive twice
                    conv.emit({"type": "subagent", "agent": d.agent_name, "state": t.split(".")[1]})
            elif t == "skill.invoked":
                conv.emit({"type": "skill", "name": d.name})
            elif t == "assistant.intent":
                conv.emit({"type": "intent", "text": d.intent})
            elif t == "assistant.usage":
                usage["model_calls"] += 1
                usage["model"] = d.model
                usage["input_tokens"] += d.input_tokens or 0
                usage["output_tokens"] += d.output_tokens or 0
            elif t == "session.compaction_complete":
                conv.emit({"type": "compaction", "success": d.success})
            elif t == "session.error":
                conv.emit({"type": "error", "message": f"{d.error_type}: {d.message}"})

        return on_event


def fixes_for(conversation_id: str) -> list[dict]:
    return db.query(
        "SELECT id, order_id, action, status, decision_note, created_at, decided_at "
        "FROM fixes WHERE conversation_id = %s ORDER BY id",
        (conversation_id,),
    )
