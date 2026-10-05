# Copilot SDK coverage: official docs vs our lessons

Sources:
- [github/copilot-sdk `docs/`](https://github.com/github/copilot-sdk/tree/main/docs) (main branch)
- [GitHub Docs: Copilot SDK](https://docs.github.com/en/copilot/how-tos/copilot-sdk)
- Installed Python SDK 1.0.16 (latest on PyPI) + runtime 1.0.90

Legend: ✅ covered and run · 🟡 partly covered · 📖 explain only (does not fit our scenario or is not released)

## 1. Building blocks

| # | Official building block | Official doc | Our coverage | Status |
|---|---|---|---|---|
| 1 | Architecture (SDK ↔ JSON-RPC ↔ runtime ↔ model) | README, `runtime-supervised-host.md` | [Architecture](sdk-architecture.md), Lesson 1 | ✅ |
| 2 | Getting started: client, session, send | `getting-started.md` | [Lesson 1](lessons/lesson-01-getting-started.md) | ✅ |
| 3 | Agent loop (turns, tool loop, idle) | `features/agent-loop.md` | Lessons 1, 3 | ✅ |
| 4 | Session persistence + resume | `features/session-persistence.md` | [Lesson 2](lessons/lesson-02-session-persistence.md) | ✅ |
| 5 | Streaming events | `features/streaming-events.md` | [Lesson 3](lessons/lesson-03-streaming-events.md) | ✅ |
| 6 | Context management (compaction, system message, plan, workspace) | `features/context-management.md` | [Lesson 4](lessons/lesson-04-context-management.md) | ✅ |
| 7 | Authentication (user, env tokens, priority) | `auth/authenticate.md` | [Lesson 5](lessons/lesson-05-auth-and-byok.md) | ✅ |
| 8 | BYOK (Foundry, OpenAI, Anthropic) | `auth/byok.md` | Lesson 5 Part D (live on Foundry) | ✅ |
| 9 | Azure Managed Identity with BYOK | `setup/azure-managed-identity.md` | Lesson 5 (`az` user token; same callback shape) | 🟡 |
| 10 | Server-to-server tokens (GitHub App, Actions) | `auth/server-to-server-tokens.md` | — | 📖 |
| 11 | Permissions (handler, request kinds, decisions) | `features/hooks.md`, getting started | [Lesson 6](lessons/lesson-06-permissions-and-tool-hooks.md) | ✅ |
| 12 | Hooks: pre / post tool use | `hooks/pre-tool-use.md`, `post-tool-use.md` | Lesson 6 | ✅ |
| 13 | Hooks: prompt submitted / transformed | `hooks/user-prompt-*.md` | [Lesson 13](lessons/lesson-13-skills-and-lifecycle-hooks.md) B | ✅ |
| 14 | Hooks: session lifecycle, error handling, agent stop | `hooks/session-lifecycle.md`, `error-handling.md` | [Lesson 13](lessons/lesson-13-skills-and-lifecycle-hooks.md) C, D | ✅ |
| 15 | Custom tools | getting started | [Lesson 7](lessons/lesson-07-custom-tools.md) | ✅ |
| 16 | Changing tools during a session (`session.set_tools`) | `features/changing-tools.md` | — (not in released Python SDK 1.0.16) | 📖 |
| 17 | Custom agents (sub-agents) | `features/custom-agents.md` | [Lesson 8](lessons/lesson-08-custom-agents.md) | ✅ |
| 18 | Fleet mode (parallel sub-agents) | `features/fleet-mode.md` | Lesson 8 shows parallel delegation | 🟡 |
| 19 | MCP servers | `features/mcp.md`, `troubleshooting/mcp-debugging.md` | [Lesson 9](lessons/lesson-09-mcp-servers.md) | ✅ |
| 20 | Skills (`SKILL.md`) | `features/skills.md` | [Lesson 13](lessons/lesson-13-skills-and-lifecycle-hooks.md) A | ✅ |
| 21 | Plugin directories (skills + hooks + MCP + agents bundle) | `features/plugin-directories.md` | — | 📖 |
| 22 | Usage and billing metrics | `features/usage-and-billing.md` | Lessons 4, 5, [10](lessons/lesson-10-observability-and-scaling.md) | ✅ |
| 23 | Session limits (AI credit cap) | `features/session-limits.md` | [Lesson 13](lessons/lesson-13-skills-and-lifecycle-hooks.md) E (cap set; minimum is 30 credits) | ✅ |
| 24 | OpenTelemetry | `observability/opentelemetry.md` | Lesson 10 | ✅ |
| 25 | Scaling + multi-tenancy | `setup/scaling.md`, `multi-tenancy.md` | Lesson 10 (parallel sessions), Lesson 5 (per-session token) | 🟡 |
| 26 | Steering and queueing | `features/steering-and-queueing.md` | [Lesson 11](lessons/lesson-11-steering-and-queueing.md) | ✅ |
| 27 | User input (`ask_user`) | getting started / API | [Lesson 12](lessons/lesson-12-user-input-and-structured-output.md) | ✅ |
| 28 | Image input (attachments) | `features/image-input.md` | [Lesson 12](lessons/lesson-12-user-input-and-structured-output.md) | ✅ |
| 29 | Structured output (`response_schema`) | Python API (`send`) | [Lesson 12](lessons/lesson-12-user-input-and-structured-output.md) | ✅ |
| 30 | Client info (app attribution) | `features/client-info.md` | [Lesson 13](lessons/lesson-13-skills-and-lifecycle-hooks.md) E | ✅ |
| 31 | Citations (experimental) | `features/citations.md` | — | 📖 |
| 32 | Remote sessions (Mission Control link) | `features/remote-sessions.md` | — (needs a GitHub repo working dir) | 📖 |
| 33 | Cloud sessions (GitHub-hosted compute) | `features/cloud-sessions.md` | — (we host on Foundry instead) | 📖 |
| 34 | Setup paths: bundled CLI, local CLI, backend, OAuth | `setup/*.md` | [Lesson 1](lessons/lesson-01-getting-started.md) (bundled runtime) | 🟡 |
| 35 | In-process runtime (experimental) | `setup/in-process-runtime.md` | — | 📖 |
| 36 | Microsoft Agent Framework integration | `integrations/microsoft-agent-framework.md` | — | 📖 |
| 37 | Troubleshooting + debugging | `troubleshooting/*.md` | Gotchas in each lesson | 🟡 |

## 2. Score

| Status | Count |
|---|---|
| ✅ Covered and run | 24 |
| 🟡 Partly | 5 |
| 📖 Explain only | 8 |
| **Total building blocks** | **37** |

## 3. Lesson 13 parts

| Part | Concept | Order 1000 example |
|---|---|---|
| A | Skills | `checkout-runbook` skill forces a fixed reply format |
| B | Prompt hook | `on_user_prompt_submitted` adds case id, tenant, tier |
| C | Lifecycle + failure hooks | start / tool-failed / end written to the App timeline |
| D | Agent-stop gate | `on_agent_stop` blocks until a `ROOT CAUSE:` line exists |
| E | Session limits + client info | Cap AI credits per case; tag the App as `checkout-harness` |

## 4. Explain-only items, in one line each

| Item | Why we do not build it now |
|---|---|
| Server-to-server tokens | For GitHub App / Actions identities. Our model calls go to Foundry (BYOK). |
| Changing tools | Shown in the docs on `main`, but `session.set_tools` is not in Python SDK 1.0.16 yet. |
| Plugin directories | Packaging of skills, hooks, MCP and agents into one folder. A packaging step for the capstone. |
| Citations | Experimental. Mainly for document-grounded answers. |
| Remote / cloud sessions | GitHub Mission Control. Our harness runs on a Foundry Hosted Agent VM. |
| In-process runtime | Experimental. Removes the child process. The Foundry VM already isolates us. |
| Microsoft Agent Framework | Wraps a Copilot session as a MAF agent. A good next step for multi-framework workflows. |
