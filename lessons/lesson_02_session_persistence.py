"""Lesson 2: client + session lifecycle.

Mirrors the Order 1000 flow (Foundry Hosted Agent, one VM per session):
  1. start client          (VM starts; SDK spawns the runtime)
  2. create session        (case session; workspace folder on disk)
  3. send a turn           (agent works)
  4. disconnect + stop     (VM goes idle; state stays on disk)
  5. NEW client + resume   (VM resumes; history comes back)
  6. delete session        (case closed; state removed)

Run: uv run python lessons/lesson_02_session_persistence.py
"""

import asyncio
import uuid

from copilot import CopilotClient
from copilot.generated.rpc import PermissionDecisionReject

# Turn 1 stores a fact. Turn 2 (in a new process) must recall it from disk.
REMEMBER_PROMPT = "Remember this case note: root cause is EXPIRED-RESERVATION. Reply only: noted."
RECALL_PROMPT = "What root cause did I note? Answer in one word."


def deny_all(request, invocation):
    # Permission handler: runs in this Python process. Lesson 2 needs no tools, so reject all.
    return PermissionDecisionReject(feedback="Lesson 2 allows no tools.")


def step(n: int, text: str) -> None:
    print(f"\n[{n}] {text}")


async def run() -> None:
    # Choose your own session id (a business key like "case-1000") so you can find it later.
    session_id = f"lesson2-case-{uuid.uuid4().hex[:8]}"

    # 1. Start client 1. Explicit start()/stop() here (no `async with`) to show each step.
    step(1, "Start client 1 (SDK starts the runtime process)")
    client1 = CopilotClient()
    seen: set[str] = set()

    def on_lifecycle(event) -> None:
        # Client-level events: session.created / updated / deleted. Print each type once.
        if event.type not in seen:
            seen.add(event.type)
            print(f"    lifecycle event: {event.type}")

    client1.on_lifecycle(on_lifecycle)
    await client1.start()
    status = await client1.get_status()
    print(f"    runtime version={status.version} protocol={status.protocol_version}")

    # 2. Create session. The runtime creates a folder: ~/.copilot/session-state/<id>.
    step(2, f"Create session {session_id}")
    session = await client1.create_session(
        session_id=session_id, model="auto", on_permission_request=deny_all
    )
    workspace = session.workspace_path
    print(f"    workspace on disk: {workspace}")

    # 3. Send one turn. History is written to the session folder.
    step(3, "Send one turn")
    reply = await session.send_and_wait(REMEMBER_PROMPT)
    if reply is None:
        raise RuntimeError("Turn 1 completed without an assistant response.")
    print(f"    assistant: {reply.data.content}")

    # 4. Disconnect frees in-memory handlers; stop ends the runtime process. Disk is kept.
    step(4, "Disconnect session + stop client 1 (like the VM going idle)")
    await session.disconnect()
    await client1.stop()
    print("    client 1 stopped. Runtime process is gone. Files stay on disk.")

    # 5. New client = new runtime process. It finds the session on disk and resumes it.
    step(5, "Start client 2 (a NEW runtime process) and resume")
    async with CopilotClient() as client2:
        ids = [s.session_id for s in await client2.list_sessions()]
        print(f"    session found on disk: {session_id in ids}")

        # Handlers are not stored on disk: pass the permission handler (and tools/hooks) again.
        resumed = await client2.resume_session(session_id, on_permission_request=deny_all)
        reply = await resumed.send_and_wait(RECALL_PROMPT)
        if reply is None:
            raise RuntimeError("Turn 2 completed without an assistant response.")
        print(f"    assistant: {reply.data.content}")
        await resumed.disconnect()

        # 6. Delete removes the session folder. Skip this step to keep it for audit.
        step(6, "Delete the session (case closed)")
        await client2.delete_session(session_id)
        meta = await client2.get_session_metadata(session_id)
        print(f"    metadata after delete: {meta}")
        print(f"    workspace folder exists: {workspace.exists() if workspace else None}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
