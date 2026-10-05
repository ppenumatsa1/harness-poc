"""Lesson 1: App -> SDK -> Runtime -> Model, in one turn.

Flow:
  1. start client     (SDK spawns the Copilot runtime; JSON-RPC over stdio)
  2. create session   (runtime creates one conversation + workspace on disk)
  3. send one turn    (runtime runs the agent loop and calls the model)
  4. print the reply  (SDK returns the final assistant.message event)

Run: uv run python lessons/lesson_01_getting_started.py
"""

import asyncio

from copilot import CopilotClient

# The prompt the App sends. The model never sees the SDK or runtime, only this text + context.
PROMPT = (
    "In two short sentences, explain why a Copilot SDK session is more than chat "
    "history. Do not use tools."
)


async def run() -> None:
    # 1. Start client: `async with` calls start() on enter and stop() on exit.
    async with CopilotClient() as client:
        # 2. Create session: model="auto" lets the runtime pick a model.
        #    `async with` disconnects the session on exit (disk state is kept).
        async with await client.create_session(model="auto") as session:
            # 3. Send one turn: send_and_wait() returns when the runtime emits session.idle.
            response = await session.send_and_wait(PROMPT)

            # The turn can finish with no assistant message (e.g. aborted or error).
            if response is None:
                raise RuntimeError("The session completed without an assistant response.")

            # 4. Print the reply: `response` is the last assistant.message event.
            print(response.data.content)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
