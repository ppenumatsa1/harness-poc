# AGENTS.md

Guide for AI coding agents working in this repo.

## Project

Hands-on lessons for the GitHub Copilot SDK (Python). Every lesson uses one scenario: **investigate why checkout failed for Order 1000**, with the agent hosted on a Foundry Hosted Agent. See [README.md](README.md) for the lesson table.

Three layers (use these words consistently):
- **App**: business truth, identity, approval. Owns the case.
- **Harness**: SDK + Copilot runtime in the VM. Runs the agent loop, context, tools, permissions, hooks.
- **Model**: stateless. Only sees what the harness sends.

## Layout

```text
lessons/lesson_NN_<topic>.py   one runnable file per lesson
lessons/checkout_fakes.py      shared fake order/payment/log data
lessons/skills/                PRODUCT skills used by the SDK agent at run time (not dev skills)
docs/lessons/lesson-NN-*.md    one doc per lesson
docs/sdk-concepts.md           learning map + progress list
docs/sdk-coverage.md           official SDK docs vs our lessons
.github/skills/                DEV skills for agents working on this repo
```

## Commands

```bash
uv sync                                     # install (SDK, mcp; dev: pillow)
uv run python lessons/lesson_NN_<topic>.py  # run a lesson (live; uses Copilot auth)
uv add <pkg>                                # add a dependency; never pip install
```

Lesson 5 Part D (BYOK) needs `az login`, `FOUNDRY_BASE_URL`, `FOUNDRY_MODEL`. Use a **reasoning** model deployment (for example `gpt-5.4-mini`); the runtime always sends a reasoning effort, and non-reasoning models return HTTP 400.

## Rules

1. **Ask before building or changing code.** Propose the plan (what, which files, why) and wait for approval. Analysis and questions need no approval.
2. **Verify every SDK fact** in the installed source (`.venv/lib/python*/site-packages/copilot/`) and the official repo/docs. Never trust web summaries or memory. Use the `verify-sdk-api` skill.
3. **Run every lesson live before writing its doc.** The "What we observed" section uses real output only.
4. **Never commit secrets**, tokens, or endpoint keys. Read config from env vars.
5. After doc edits, run the `validate-docs` skill (Mermaid + links).
6. Keep README, `docs/sdk-concepts.md`, and `docs/sdk-coverage.md` in sync when lessons change.

## Lesson code conventions

- Module docstring: one-line title, numbered steps or parts (A, B, C...), scenario line, `Run:` command.
- Prompt constants at the top; `async def run()` + `def main()` + `if __name__ == "__main__": main()`.
- Lean sessions: `available_tools=[t.name for t in tools]` plus any built-ins needed (`ask_user`, `skill`, `task`), and a `deny_all` permission handler unless the lesson is about permissions.
- Reuse Lesson 7 tools: `from lesson_07_custom_tools import get_order, get_payment, get_logs`.
- Check `reply is None` before reading `reply.data.content`.
- Comments only where the SDK behavior is non-obvious.

## Lesson doc template (`docs/lessons/lesson-NN-<topic>.md`)

Header: `Code:` link and `Run:` command. Then these 8 sections:

1. Story (simple): numbered, short sentences, ends with a one-line **Rule**.
2. Diagram: one Mermaid diagram.
3. Table: the key comparison for the lesson.
4. API map: Goal → Code.
5. What we observed: real output in a `text` block, then **Gotchas**.
6. Map to the Order 1000 scenario (Foundry Hosted Agent).
7. Remember: 4–5 bullets.
8. Try it (one safe extension).

## Versions

`github-copilot-sdk` 1.0.16, runtime 1.0.90 (protocol 3). Recheck with the `sdk-upgrade-check` skill before relying on newer features.
