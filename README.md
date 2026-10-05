# Copilot SDK Learning Lab (Python)

Hands-on lessons for the [GitHub Copilot SDK](https://github.com/github/copilot-sdk), built step by step around one scenario: **investigate why checkout failed for Order 1000**, with the agent hosted on a Foundry Hosted Agent.

Method: clear writing → diagram → runnable code → observed output → interactive simulation (for the hard parts).

## Quick start

```bash
uv sync                                         # SDK, mcp, pillow (dev)
uv run python lessons/lesson_01_getting_started.py      # any lesson runs the same way
```

Requires: Python 3.11+, [uv](https://docs.astral.sh/uv/), and a GitHub login with Copilot access (`gh auth login` or `COPILOT_GITHUB_TOKEN`).
Lesson 5 Part D (BYOK) also needs `az login` plus `FOUNDRY_BASE_URL` and `FOUNDRY_MODEL` (use a reasoning model, for example `gpt-5.4-mini`).

## Start here (big picture)

| Doc | What it gives you |
|---|---|
| [Architecture](docs/sdk-architecture.md) | App → SDK → runtime → model, end to end |
| [Architecture views](docs/sdk-architecture-views.md) | The same system from several angles |
| [Components](docs/sdk-components.md) | Each building block in one line |
| [Architecture quiz](docs/sdk-architecture-quiz.md) | Check your understanding |
| [Scenario: Order 1000](docs/scenario-checkout-order-1000.md) | The shared story for all lessons |
| [Interactive simulation](docs/explainer-checkout-flow.html) | Open in a browser. Step through who does what (App / harness / model / tools / VM) |
| [Learning map](docs/sdk-concepts.md) | Concept path and progress |
| [Coverage vs official docs](docs/sdk-coverage.md) | Each official building block → our lesson |

## Lessons

| # | Concept | Code | Doc |
|---|---|---|---|
| 1 | Getting started: one turn, App → SDK → runtime → model | [lesson_01_getting_started.py](lessons/lesson_01_getting_started.py) | [lesson-01-getting-started.md](docs/lessons/lesson-01-getting-started.md) |
| 2 | Session persistence: client + session lifecycle, resume | [lesson_02_session_persistence.py](lessons/lesson_02_session_persistence.py) | [lesson-02-session-persistence.md](docs/lessons/lesson-02-session-persistence.md) |
| 3 | Streaming events | [lesson_03_streaming_events.py](lessons/lesson_03_streaming_events.py) | [lesson-03-streaming-events.md](docs/lessons/lesson-03-streaming-events.md) |
| 4 | Context management | [lesson_04_context_management.py](lessons/lesson_04_context_management.py) | [lesson-04-context-management.md](docs/lessons/lesson-04-context-management.md) |
| 5 | Authentication + BYOK on Foundry | [lesson_05_auth_and_byok.py](lessons/lesson_05_auth_and_byok.py) | [lesson-05-auth-and-byok.md](docs/lessons/lesson-05-auth-and-byok.md) |
| 6 | Permissions + tool hooks (pre/post) | [lesson_06_permissions_and_tool_hooks.py](lessons/lesson_06_permissions_and_tool_hooks.py) | [lesson-06-permissions-and-tool-hooks.md](docs/lessons/lesson-06-permissions-and-tool-hooks.md) |
| 7 | Custom tools | [lesson_07_custom_tools.py](lessons/lesson_07_custom_tools.py) | [lesson-07-custom-tools.md](docs/lessons/lesson-07-custom-tools.md) |
| 8 | Custom agents (sub-agents) | [lesson_08_custom_agents.py](lessons/lesson_08_custom_agents.py) | [lesson-08-custom-agents.md](docs/lessons/lesson-08-custom-agents.md) |
| 9 | MCP servers | [lesson_09_mcp_servers.py](lessons/lesson_09_mcp_servers.py), [checkout_mcp_server.py](lessons/checkout_mcp_server.py) | [lesson-09-mcp-servers.md](docs/lessons/lesson-09-mcp-servers.md) |
| 10 | Observability + scaling: health, errors, cost, telemetry | [lesson_10_observability_and_scaling.py](lessons/lesson_10_observability_and_scaling.py) | [lesson-10-observability-and-scaling.md](docs/lessons/lesson-10-observability-and-scaling.md) |
| 11 | Steering and queueing | [lesson_11_steering_and_queueing.py](lessons/lesson_11_steering_and_queueing.py) | [lesson-11-steering-and-queueing.md](docs/lessons/lesson-11-steering-and-queueing.md) |
| 12 | User input (ask_user, images) + structured output | [lesson_12_user_input_and_structured_output.py](lessons/lesson_12_user_input_and_structured_output.py) | [lesson-12-user-input-and-structured-output.md](docs/lessons/lesson-12-user-input-and-structured-output.md) |
| 13 | Skills + lifecycle hooks (prompt, session, error, stop), limits, client info | [lesson_13_skills_and_lifecycle_hooks.py](lessons/lesson_13_skills_and_lifecycle_hooks.py), [SKILL.md](lessons/skills/checkout-runbook/SKILL.md) | [lesson-13-skills-and-lifecycle-hooks.md](docs/lessons/lesson-13-skills-and-lifecycle-hooks.md) |
| — | Capstone: Order 1000 investigation app using all concepts | [lessons/capstone/](lessons/capstone/) | [capstone.md](docs/capstone.md) (local; Hosted Agents and [background features](docs/sdk-concepts.md#5-revisit-before-the-capstone) later) |

Shared fake data: [checkout_fakes.py](lessons/checkout_fakes.py). Lessons 8–13 reuse the Lesson 7 tools.

## Layout

```text
lessons/           runnable code (one file per lesson) + skills/
docs/              big-picture docs, scenario, simulation, coverage
docs/lessons/      one doc per lesson: story, diagram, API map, observed output, try it
```

Versions used: `github-copilot-sdk` 1.0.16, runtime 1.0.90.
