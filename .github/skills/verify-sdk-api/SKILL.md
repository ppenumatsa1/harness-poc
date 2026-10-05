---
name: verify-sdk-api
description: Verify a GitHub Copilot SDK (Python) API, parameter, hook, event, or feature against the installed source and official docs before using or explaining it. Use for any SDK claim, especially when docs, memory, or web summaries may be outdated.
---

# Verify an SDK API

Source of truth order: **installed source > official repo docs/changelog > GitHub Docs > anything else.** Web search summaries are hints only. They have invented features before (for example, a "SDK 2.0" that does not exist).

1. **Installed version**
   ```bash
   uv pip show github-copilot-sdk | head -2
   ```
2. **Search the installed source** (`P=$(ls -d .venv/lib/python*/site-packages/copilot)`):
   - Client options and `create_session` params: `$P/client.py`
   - `send`, hooks (`class SessionHooks`), hook input/output TypedDicts: `$P/session.py`
   - Event data classes: `$P/generated/session_events.py`
   - RPC methods (`session.rpc.*`): `$P/generated/rpc.py`
   ```bash
   grep -rn "<name>" --include=*.py $P | head
   ```
3. **Official docs** (main branch may be ahead of the release):
   - `https://raw.githubusercontent.com/github/copilot-sdk/main/docs/<area>/<topic>.md`
   - `https://raw.githubusercontent.com/github/copilot-sdk/main/CHANGELOG.md`
4. **Classify** the result and say it explicitly:
   - ✅ in the installed SDK
   - 🟡 in docs/main or a preview release only
   - ❌ not found
5. If behavior matters, **prove it with a small live run** (a `/tmp` script that imports from `lessons/`; set `PYTHONPATH=lessons`). Delete the script after.

Known gotchas already verified:
- BYOK: the runtime always sends a reasoning effort; non-reasoning models fail with 400.
- `response_schema` with OpenAI models needs `ConfigDict(extra="forbid")`.
- `session_limits.max_ai_credits` minimum is 30.
- `subagent.completed` arrives twice; de-duplicate by `tool_call_id`.
