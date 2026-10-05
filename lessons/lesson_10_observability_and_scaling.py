"""Lesson 10: operations (health, scale, errors, cost, telemetry, cleanup).

What you need before the Order 1000 harness can run for real users:
  A. Health     : is the runtime up and on the protocol version we expect?
  B. Scale      : one client, many sessions, running in parallel.
  C. Errors     : a tool fails; a turn is too slow (timeout -> abort -> session still usable).
  D. Cost       : per-session token and request metrics.
  E. Telemetry  : OpenTelemetry spans from the runtime (file exporter here; OTLP in production).
  F. Cleanup    : delete finished sessions so the disk does not fill up.

Run: uv run python lessons/lesson_10_observability_and_scaling.py
"""

import asyncio
import json
import tempfile
import time
from collections import Counter
from pathlib import Path

from copilot import CopilotClient, define_tool
from copilot.generated.rpc import PermissionDecisionReject
from copilot.session_events import ToolExecutionCompleteData
from lesson_07_custom_tools import OrderId, get_logs, get_order, get_payment  # reuse Lesson 7 tools

QUESTIONS = [  # three "support tickets" handled in parallel
    "What is the status of order 1000? One line.",
    "Was the payment for order 1000 authorized and captured? One line.",
    "Quote the failing log line for order 1000. One line.",
]


@define_tool(description="Get the refund policy that applies to an order.", skip_permission=True)
def get_refund_policy(params: OrderId) -> str:
    raise RuntimeError("policy service unavailable (HTTP 503)")  # simulate a broken dependency


def deny_all(request, invocation):
    return PermissionDecisionReject(feedback="Not allowed in Lesson 10.")


def lean_session(client, tools):
    # Lean = only our tools, no built-ins: small context, cheap, safe (Lessons 4, 6, 7).
    return client.create_session(
        model="auto", tools=tools, available_tools=[t.name for t in tools], on_permission_request=deny_all
    )


async def ask(client, question: str) -> tuple[str, str, float]:
    start = time.perf_counter()
    session = await lean_session(client, [get_order, get_payment, get_logs])
    async with session:
        reply = await session.send_and_wait(question, timeout=180)
        metrics = await session.rpc.usage.get_metrics()  # D. cost per session
        tokens = sum(m.usage.input_tokens + m.usage.output_tokens for m in metrics.model_metrics.values())
        answer = reply.data.content.strip() if reply else "(no reply)"
        print(f"  [{session.session_id[:8]}] {time.perf_counter() - start:5.1f}s tokens={tokens:>6} {answer}")
        return session.session_id, answer, time.perf_counter() - start


async def run() -> None:
    trace_file = Path(tempfile.mkdtemp(prefix="lesson10-")) / "traces.jsonl"
    # E. Telemetry is a CLIENT setting: it is passed to the runtime process as OTEL env vars.
    telemetry = {"exporter_type": "file", "file_path": str(trace_file), "source_name": "checkout-harness"}
    created: list[str] = []

    async with CopilotClient(telemetry=telemetry) as client:
        # A. Health
        status = await client.get_status()
        pong = await client.ping("health")
        print(f"\n=== A. Health ===\n  runtime {status.version} protocol {status.protocol_version}; ping -> {pong.message}")

        # B. Scale: three sessions at once on ONE client (one runtime process).
        print("\n=== B. Scale: 3 sessions in parallel ===")
        start = time.perf_counter()
        results = await asyncio.gather(*(ask(client, q) for q in QUESTIONS))
        wall, total = time.perf_counter() - start, sum(r[2] for r in results)
        print(f"  wall clock {wall:.1f}s vs {total:.1f}s if run one by one")
        created += [r[0] for r in results]

        # C1. A tool fails. The SDK turns the exception into a failed tool result; the model adapts.
        print("\n=== C1. Error: tool raises ===")
        async with await lean_session(client, [get_refund_policy]) as session:
            created.append(session.session_id)
            session.on(
                lambda e: isinstance(e.data, ToolExecutionCompleteData)
                and print(f"  tool-done   success={e.data.success} error={e.data.error.message if e.data.error else None}")
            )
            reply = await session.send_and_wait("What refund policy applies to order 1000? One line.", timeout=120)
            print(f"  reply       {reply.data.content.strip() if reply else '(none)'}")

        # C2. A turn is too slow. Timeout only stops WAITING; abort() stops the WORK.
        print("\n=== C2. Error: timeout -> abort -> continue ===")
        async with await client.create_session(
            model="auto", available_tools=[], on_permission_request=deny_all
        ) as session:
            created.append(session.session_id)
            idle = asyncio.Event()
            session.on(lambda e: e.type.value == "session.idle" and idle.set())
            try:
                await session.send_and_wait("Write a 2000-word essay about payment systems.", timeout=3)
            except TimeoutError:
                print("  send_and_wait timed out after 3s -> session.abort()")
                idle.clear()
                await session.abort()
                await asyncio.wait_for(idle.wait(), 30)  # let the aborted turn settle before the next send
                print("  aborted turn reached session.idle")
            reply = await session.send_and_wait("Reply with exactly: still alive", timeout=60)
            print(f"  same session after abort: {reply.data.content.strip() if reply else '(none)'}")

        # F. Cleanup: sessions stay on disk after disconnect (Lesson 2). Delete what we made.
        print("\n=== F. Cleanup ===")
        before = len(await client.list_sessions())
        for session_id in created:
            await client.delete_session(session_id)
        print(f"  deleted {len(created)} sessions; listed {before} -> {len(await client.list_sessions())}")

    # E. Read the spans after the client stopped (the runtime flushes on exit).
    print("\n=== E. Telemetry (OpenTelemetry file exporter) ===")
    lines = trace_file.read_text().splitlines() if trace_file.exists() else []
    records = [json.loads(line) for line in lines]
    # Keep the GenAI semantic-convention spans; skip runtime-internal session.timing.* spans.
    kinds = Counter(r["attributes"].get("gen_ai.operation.name") for r in records if r.get("type") == "span")
    kinds.pop(None, None)
    metrics = sorted({r["name"] for r in records if r.get("type") != "span" and r["name"].startswith("gen_ai")})
    print(f"  {len(records)} records in {trace_file.name}")
    print(f"  gen_ai spans by operation: {dict(kinds)}")
    print(f"  gen_ai metrics: {metrics}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
