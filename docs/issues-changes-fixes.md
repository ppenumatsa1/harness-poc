# Copilot SDK learning: issues, changes and fixes

This file records what broke, what we changed, and what we learned. Newest entries come first.
Each table row is one issue. Read the "Learning" column first if you are short on time.

- SDK: `github-copilot-sdk` 1.0.16 (Python), runtime 1.0.90.
- Model: BYOK to Foundry `gpt-5.4-mini` on `cog-clpttynzwwraw` (RG `rg-crcopilot-20260920`).
- Capstone code: [`lessons/capstone/`](../lessons/capstone/).

## 2026-10-04 - Capstone local verification

**Live end-to-end passed** through `http://localhost:5173` (web → api → agent → Postgres, with the model on Foundry).

| Gate | Result |
| --- | --- |
| Agent tests (`docker compose run --rm --no-deps agent pytest -q`) | **33 passed** (guards, DB tools, harness lock and Finding checks) |
| API tests | **8 passed** (SSE relay, validation, 404, health) |
| Web | `tsc` type check and `vite build` passed |
| Order 1001 (healthy) | `NO_FAILURE`, no fix proposed, no false fact-check errors |
| Order 1000 | `RESERVATION_EXPIRED`; fix #6 proposed → **approve** → status `applied` |
| Order 1002 | `CARD_DECLINED`; fix #7 proposed → **reject** with a note → status `rejected`, note stored |
| Client disconnect | Agent logged `turn interrupted; aborting session case-…`; no error |
| Stop gate | Did not fire wrongly during the sub-agent runs |
| App Insights (`crcopilot-xfvhibddvclsw-appi`) | One `operation_Id` holds `checkout-api` and `checkout-agent` spans: `POST /api/investigate` → `POST /invoke` → `invoke_agent investigate` → `execute_tool skill/task/get_order/get_payment/get_inventory/logs-get_logs/propose_fix` → `SELECT` |
| Cost per investigation | ~25K input tokens, ~1.4K output, 8 model calls, 60–140 s (most of it is waiting on 429s) |

### Rubber-duck review fixes (11 findings)

| Issue | Change and learning |
| --- | --- |
| A second request on a busy conversation reset the state of the running turn and wrote to the DB before it checked the lock | `investigate()` and `decide()` now take the per-conversation lock **first**. Then they reset state or write the DB. **Learning:** check the guard before any side effect. Tests: `test_busy_conversation_*`. |
| `proposed_fix` was set in the permission handler, before the tool ran. A failed insert still counted as "proposed" | The flag is now set in `on_post_tool_use`, only when the result contains `fix_id`. **Learning:** permission says "may run", the post-tool hook says "did run". |
| A client disconnect cancelled the Python waiter, but the runtime kept running the turn (and spent tokens) | The `finally` block calls `session.abort()` (10 s timeout), then cancels and gathers the task. **Learning:** cancelling `send` does not stop the runtime; only `abort()` does. |
| The model could return a Finding for the wrong order or invent a `fix_id` | `_check_finding()` checks the order id, that the fix id belongs to this conversation, and that a failure has a fix. Problems are sent as an `error` event. **Learning:** the schema checks the shape, not the facts. |
| An approval whose follow-up turn failed left the fix stuck in `approved` | `decide` accepts `approved` again for a retry. The UI shows the approval bar for `pending` or `approved`. |
| Browser SSE parser: `\r\n` not handled, last frame lost at end of stream, a cut stream looked like success | `sse.ts` normalises line endings, processes the leftover buffer, and throws if no `done` event arrived. |
| Abort could hang | `asyncio.wait_for(session.abort(), 10)`. |
| Accepted, not fixed (#3) | The raw card number is selected on purpose, to show post-tool redaction. The data is fake seed data. |
| Accepted (#5) | Sessions and caches grow without a limit. OK for a local lab. |
| Accepted (#9) | Sync `psycopg2` calls run inside async code. OK at lab load. |
| Accepted (#10) | Role passwords are set only on the first DB init. To change them, run `ALTER ROLE` or delete the volume. |

### Bugs found by live runs

| Issue | Change and learning |
| --- | --- |
| **Stop gate used up by a sub-agent.** `on_agent_stop` fires for sub-agent stops too, and its input does not say which agent is stopping. The gate's single "block" went to a sub-agent, so the main agent could stop without `propose_fix`. | Track `conv.active_subagents` from `subagent.started/completed/failed` events. Skip the gate while any sub-agent is running. Test added. **Learning:** in 1.0.16, assume every lifecycle hook can fire for sub-agents. |
| Health check always failed | `client.ping("health").message` is `"pong: health"`, not `"health"`. The check now uses `.endswith("health")`. The compose healthcheck asserts `status == "ok"`. |
| **429 rate limits.** Each turn waits 30–80 s | The deployment is GlobalStandard with capacity 10 (10K TPM). One investigation uses ~25K tokens. The runtime retries by itself; the retries show up as `hook error model_call` events. **Not changed:** raising capacity needs your OK. |
| The Finding's `first_failure_log` sometimes has extra quotes or backticks | Minor model formatting. Not fixed. |

### Container and environment issues

| Issue | Change and learning |
| --- | --- |
| **TLS handshake failure from containers** to `files.pythonhosted.org` and `registry.npmjs.org` (the host works; the containers use OpenSSL 3.5.6). Pinned IPs, `--network host` and limited ciphers did not help. | Use the Microsoft feeds (see [model-to-harness notes](https://github.com/ppenumatsa1/model-to-harness/blob/main/agent-framework/double-charge/maf/docs/design/issues-changes-fixes.md)): `ARG PIP_FEED=https://packagefeedproxy.microsoft.io/pypi/simple/` → `UV_INDEX_URL`, and `.npmrc` `registry=https://packagefeedproxy.microsoft.io/npm/`. **Do not force the mirror on Foundry Hosted Agents.** |
| The mirror has no `github-copilot-sdk==1.0.16` (it has only `1.0.16rc0` and `1.0.17rc*`) | Downloaded the wheel on the host into `agent/wheels/`. Install with `--find-links ./wheels`. |
| The mirror stops at `mcp` 2.2.0, `httpx` latest is `1.0.dev`, and `typescript` latest is 7.x | `mcp>=2.2.0` (checked: `MCPServer` and `ToolAnnotations` exist), `httpx<1`, `typescript ~5.9.3`. **Learning:** pin against what the mirror has. |
| npm lockfile URLs say `registry.npmjs.org` | No change needed: npm swaps the host for the `.npmrc` registry. |
| Agent start was very slow | `~/.azure` links to the Windows drive (723 MB). `entrypoint.sh` now copies only `azureProfile.json`, `msal_token_cache.json`, `msal_http_cache.bin`, `config`, `clouds.config`, `az.json`, `az.sess`. |
| `create_session` failed with `EACCES` | The named volume at `/home/app/.copilot` was owned by root. Fix: `RUN mkdir -p /home/app/.copilot` as user `app` in the Dockerfile, then recreate the volume. **Learning:** a new named volume copies the owner of the image's directory. |
| Port 5432 already used by another project | Stopped (not removed) 10 other containers. `docker start <name>` brings them back. DB port is `${DB_HOST_PORT:-5432}`. |
| Very noisy logs | Set `azure.core.pipeline.policies.http_logging_policy` and `azure.monitor.opentelemetry.exporter` to WARNING. |

### UI, repo hygiene and capacity (same day, later)

| Issue | Change and learning |
| --- | --- |
| 429 retries made one investigation take 60–140 s at 10K TPM | You raised `gpt-5.4-mini` to 400K TPM. The first run still had 3 retries (the change was spreading). Later runs: **0 retries, about 29 s**. **Learning:** one investigation uses about 25K input tokens; size TPM for parallel cases. |
| 73 old containers from other projects | Removed with `docker rm -f`. Volumes and images were kept. Only the 4 capstone containers remain. |
| The UI looked too basic | Rebuilt the web UI in the style of `explainer-checkout-flow.html`: white, role colours, top bar with health, order list, stats, 7-step stepper, "who is working now" stage, agent lanes, guardrails feed, finding card, decision panel, raw event stream. No new npm packages. Checked with Playwright screenshots (0 console errors). |
| Downloaded files could be committed (SDK wheel, caches, `.env`) | Rewrote `.gitignore` (`*.whl`, `agent/wheels/*` with `!.gitkeep`, `.env*` with `!.env.example`, keys, node, build output, logs, `.azure/`, `.foundry/`). Added `agent/fetch_wheels.sh` to download the wheel again. Checked with `git check-ignore`. |
| Taking screenshots: no browser on the host, npm blocked | Ran `mcr.microsoft.com/playwright:v1.62.1-noble` with `--network host` and installed `playwright-core` from the npm mirror. |
| Capstone docs missing | Wrote [capstone.md](capstone.md) and the [capstone README](../lessons/capstone/README.md). |

## 2026-10-05 - Review limits fixed

| Issue | Change and learning |
| --- | --- |
| Sync `psycopg2` calls blocked the event loop (#9). The SDK calls sync tool handlers directly (`result = fn(...)`), so one slow query froze every case. | `db.aquery/aquery_one/awrite` run the call with `asyncio.to_thread`. Tools, the permission handler, `/health`, `/invoke` and the harness use them. **Learning:** tool and permission handlers may be `async`; the SDK awaits them. |
| Sessions grew forever (#5), and each resume listed all sessions. | Use `get_session_metadata(sid)` (one lookup). `close_case` disconnects and calls `delete_session` when every fix is applied or rejected; an approved-but-not-applied fix keeps the session for a retry. A sweeper deletes cases idle for `SESSION_TTL_H` (24h). Live: approve → `closed case … session deleted`, folder gone. |
| Role passwords were set only on first init (#10), and passwords were env vars (visible in `docker inspect`). | `./make_secrets.sh` writes random hex passwords to `secrets/` (git-ignored, folder 700). Compose `secrets:` + `*_FILE` vars. A `db-roles` one-shot runs `ALTER ROLE` on every `up`. Checked: 0 password env vars in `docker inspect`; rotating `app_ro` + `up -d --force-recreate` → health ok. |
| `db-roles` failed with "connection refused" | The healthcheck `pg_isready` used the socket, which is up during first-start init (TCP is off then). Use `pg_isready -h 127.0.0.1`. |
| Replaced files did not reach running containers | A file bind mount keeps the old inode. Use `--force-recreate` after rotating. |
| `get_payment` returned the raw card on purpose (#3) | The tool now returns `'**** ' || right(card_number, 4)`. The demo moved to a realistic leak: a `payment-gw` log line with the full card. The post-tool hook redacts the MCP `logs-get_logs` result. Live: "redacted card number in logs-get_logs result", raw card count in the stream = 0. |

Tests: agent 38 passed (5 new), API 8 passed. Live 1000: `RESERVATION_EXPIRED`, 8 model calls, 25.3K/1.4K tokens, 28.6 s; approve → applied.

## Lessons 1–13 (earlier sessions)

| Issue | Change and learning |
| --- | --- |
| BYOK with `gpt-4.1-mini` returned HTTP 400 on both wire APIs | The runtime **always** sends a reasoning effort (`responses`: `reasoning.effort=medium`; `completions`: `reasoning_effort`). It was confirmed with a fake capture server. Use a reasoning model (`gpt-5.4-mini`). |
| `az login` expired (conditional-access refresh token) | The BYOK wiring was checked against a local fake server; the 401 showed as a session error. An interactive `az login` fixed it. |
| `response_schema=Finding` returned 400 "additionalProperties … must be false" | Add `model_config = ConfigDict(extra="forbid")` to the Pydantic model. |
| `mcp` 2.x renamed `FastMCP` | Use `mcp.server.mcpserver.MCPServer`, with `server.run("stdio")`. |
| `send_and_wait` timeout | It raises `TimeoutError` but does **not** stop the work. Use `session.abort()`. |
| A failing tool did not call `on_error_occurred` | Tool failures fire `on_post_tool_use_failure`. A tool exception gives `success=False`, "Tool execution failed". |
| Lesson 6 pre-hook denied safe writes | The hook checked file content. It now checks only targets (paths, commands, `apply_patch` file headers). |
| The model refused to read a file named `secrets` | Renamed it `app.env`. General rejection feedback made the model skip the step; specific feedback fixed it. |
| `approve_all` raised under managed settings | Use a custom permission handler. |
| Sub-agent labels were wrong in the timeline | Map `event.agent_id` from `subagent.started`. |
| The file-write tool name depends on the model | Match several tool names in hooks. |
| Lesson names did not match GitHub Copilot feature names | Renamed lessons 2–10 to the docs' names, split Lesson 11 into 11 (steering + queueing) and 12 (user input + structured output), and moved old 12 to 13 (skills + lifecycle hooks). |
| Explainer HTML: SVG overlay not sized, a VM tag wrapped | Set width/height to 100%; checked with puppeteer screenshots. |

## Open items

- [x] Raise TPM on the `gpt-5.4-mini` deployment (400K TPM; 0 retries).
- [x] Write `docs/capstone.md` and `lessons/capstone/README.md`; update the root README and `sdk-concepts.md`.
- [x] Accepted review limits fixed on 2026-10-05 (see the section above). Was: accepted review limits (lab only): sessions not trimmed, sync DB calls in async code, role passwords set only at first DB start, raw card read on purpose for the redaction demo. Decide if any must be fixed before the push.
- [x] Push to `https://github.com/ppenumatsa1/harness-poc.git` (2026-10-04, commit `e5f6112`).
- [ ] Later: move the agent to Foundry Hosted Agents; revisit the 5 background SDK features and the 1.0.17 upgrade.
