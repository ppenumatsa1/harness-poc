"""Lesson 5: auth + models.

Two separate questions:
  A. Who is the caller?        (auth: GitHub identity -> Copilot-hosted models)
  B. Which models can I use?   (list_models: id, context window, reasoning, billing)
  C. Pick and switch a model   (create_session(model=..., reasoning_effort=...) + set_model)
  D. Bring your own model      (BYOK provider: Microsoft Foundry; no GitHub model billing)

Auth priority (highest first): github_token argument -> GITHUB_COPILOT_API_TOKEN ->
COPILOT_GITHUB_TOKEN / GH_TOKEN / GITHUB_TOKEN -> stored `copilot` login -> `gh auth`.

Part D runs only when FOUNDRY_BASE_URL and FOUNDRY_MODEL are set, e.g.:
  export FOUNDRY_BASE_URL=https://<resource>.openai.azure.com/openai/v1/
  export FOUNDRY_MODEL=<deployment-name>      # a reasoning model, e.g. gpt-5.4-mini
It uses your `az login` identity (Entra ID bearer token). No API key.

Run: uv run python lessons/lesson_05_auth_and_byok.py
"""

import asyncio
import os
import subprocess

from copilot import CopilotClient
from copilot.generated.rpc import PermissionDecisionReject
from copilot.session_events import AssistantUsageData

PROMPT = "Reply with one short sentence: which model family are you?"


def deny_all(request, invocation):
    # No tools needed in this lesson. Permissions are Lesson 6.
    return PermissionDecisionReject(feedback="Lesson 5 allows no tools.")


def track_model(session) -> list[str]:
    # assistant.usage tells you which model really served each call (important with "auto").
    used: list[str] = []
    session.on(lambda e: used.append(e.data.model) if isinstance(e.data, AssistantUsageData) else None)
    return used


async def ask(session, prompt: str) -> str:
    reply = await session.send_and_wait(prompt, timeout=120)
    if reply is None:
        raise RuntimeError("Turn completed without an assistant response.")
    return reply.data.content


def azure_token(args) -> str:
    # bearer_token_provider callback: the runtime calls it when it needs a fresh token.
    # Production: use azure-identity (managed identity in the Foundry Hosted Agent VM).
    out = subprocess.run(
        ["az", "account", "get-access-token", "--resource", "https://cognitiveservices.azure.com",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


async def run() -> None:
    async with CopilotClient() as client:
        # A. Auth: the client authenticates once. Sessions inherit it (or pass github_token per session).
        print("\n=== A. Auth ===")
        auth = await client.get_auth_status()
        print(f"  authenticated={auth.isAuthenticated} type={auth.authType} login={auth.login}")

        # B. Models: what this identity is allowed to use, with limits and billing.
        print("\n=== B. Models (first 8) ===")
        models = await client.list_models()
        ids = [m.id for m in models]
        print(f"  {len(models)} models available (incl. 'auto' = runtime picks per call)")
        for m in [m for m in models if m.id != "auto"][:8]:
            limits = m.capabilities.limits
            policy = m.policy.state if m.policy else None
            print(
                f"  {m.id:<20} context={limits.max_context_window_tokens} "
                f"policy={policy} reasoning={m.supported_reasoning_efforts}"
            )

        # C. Pick a model for the session, then switch it mid-session. History is kept.
        print("\n=== C. Pick + switch model ===")
        first = "auto"
        second = "claude-haiku-4.5" if "claude-haiku-4.5" in ids else ids[1]  # small + fast
        async with await client.create_session(
            model=first, on_permission_request=deny_all, available_tools=[]
        ) as s:
            used = track_model(s)
            print(f"  [{first}] {await ask(s, PROMPT)}")
            await s.set_model(second)  # next model call uses the new model
            print(f"  [{second}] {await ask(s, PROMPT)}")
            print(f"  assistant.usage models: {used}")

        # D. BYOK: the runtime calls your provider directly. Copilot auth still starts the
        #    runtime, but inference + billing go to your Foundry resource.
        print("\n=== D. BYOK: Microsoft Foundry ===")
        base_url, model = os.getenv("FOUNDRY_BASE_URL"), os.getenv("FOUNDRY_MODEL")
        if not (base_url and model):
            print("  skipped: set FOUNDRY_BASE_URL and FOUNDRY_MODEL to run this part")
            return
        async with await client.create_session(
            model=model,  # Foundry deployment name
            on_permission_request=deny_all,
            available_tools=[],
            provider={
                "type": "openai",  # Foundry /openai/v1/ endpoint is OpenAI-compatible
                # The runtime always sends a reasoning effort, so the deployment must be a
                # reasoning model (gpt-5.x / o-series). gpt-4.1-mini fails with HTTP 400.
                "base_url": base_url,
                "wire_api": "responses",
                "bearer_token_provider": azure_token,  # Entra ID; no API key in code
            },
        ) as s:
            used = track_model(s)
            print(f"  [foundry:{model}] {await ask(s, PROMPT)}")
            print(f"  assistant.usage models: {used}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
