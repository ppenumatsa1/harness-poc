---
name: html-simulation
description: Build a self-contained interactive HTML explainer or simulation for a complex Copilot SDK / harness concept (who does what across App, Harness, Model, tools, VM). Use when a concept has many actors, states, or steps, or when the user asks to visualize or simulate a flow.
---

# HTML simulation

Reference example: `docs/explainer-checkout-flow.html` (the user found it the clearest format). Match its approach.

## Before building

1. Write the flow as numbered steps first (actor → action → data). Confirm the steps are true using the `verify-sdk-api` skill or a live run.
2. Propose the steps and the layout to the user; wait for approval.

## Design rules

- **One file**, no build step, no external network calls (inline CSS/JS; no CDN).
- **Color code by layer**, the same colors in every simulation:
  App / human, Harness (SDK + runtime), Model, Tools / MCP / external services, VM / infra.
- **Layout**: use the full width. Use a CSS grid: actor lanes or a diagram on the left, a **wide** detail panel on the right (at least about 40% of the width). Avoid large empty areas. The user rejected a narrow side panel.
- **Controls**: Play, Pause, Step forward/back, Reset, and a scenario picker when there are variants (for example "allowed" vs "denied" tool call).
- **Each step shows**: which actor is active (highlight), the message or event name (real SDK names, e.g. `tool.execution_start`), the payload snippet, and one plain-language sentence.
- Make it readable at 1280px and 1920px wide.

## Placement and checks

- Save as `docs/explainer-<topic>.html`. Link it from the related lesson doc and the README "Start here" table.
- Open-check: load the file in a headless browser or at least parse it (`python3 -c "import html.parser"`), and step through every scenario to make sure no step throws an error.
