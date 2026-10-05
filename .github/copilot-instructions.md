# Copilot instructions

This repo is a **learning lab**. The user learns the Copilot SDK step by step. Project rules and conventions are in [AGENTS.md](../AGENTS.md); follow them.

## How to explain (Karpathy-style progression)

Use the simplest form that makes the idea clear. Go further only when it helps understanding or verification:

1. Clear writing: short sentences, explicit terms (about 60–70% of ASD-STE100 style).
2. Diagram: Mermaid flows, sequences, state machines.
3. Interactive HTML explainer or simulation: the default for complex harness concepts (use the `html-simulation` skill).
4. Explainer video: only for motion-heavy concepts.

For a new concept:
- Start with a short story.
- Then a comparison table.
- Then what the options share, and the key insights.
- Prefer numbered A → B → C flows over ASCII box art.

## Response style

- Short answers first; expand only when asked.
- Tie every concept to the Order 1000 checkout scenario and the App / Harness / Model layers.
- Say clearly what is verified (source, live run) and what is not (no transcript, preview-only, web summary).

## Workflow

- Analysis, summaries, and questions: do them directly.
- Code or file changes: propose first, wait for approval (see AGENTS.md rule 1).
- New lesson: use the `new-lesson` skill. SDK facts: `verify-sdk-api`. Docs: `validate-docs`. New SDK release: `sdk-upgrade-check`.
