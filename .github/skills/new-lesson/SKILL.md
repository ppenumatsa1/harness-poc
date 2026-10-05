---
name: new-lesson
description: Add a new Copilot SDK lesson to this learning lab (code + live run + doc + index updates). Use when asked to add, build, or extend lesson N or a new SDK concept lesson.
---

# New lesson

Steps 1–2 need **user approval** before you write code.

1. **Scope.** Read `docs/sdk-coverage.md` and `docs/sdk-concepts.md`. Pick the concept and the parts (A, B, C...). Map each part to the Order 1000 scenario.
2. **Verify the API.** Use the `verify-sdk-api` skill for every class, parameter, hook, and event you plan to use. Then **propose the plan to the user**: file names, parts, expected observations. Wait for approval.
3. **Code** `lessons/lesson_NN_<topic>.py` following the conventions in `AGENTS.md`:
   - Docstring with parts and `Run:` line.
   - Reuse `lesson_07_custom_tools` and `checkout_fakes`.
   - Lean session: `available_tools`, a `deny_all` handler.
   - Print short labeled lines (`  call  ...`, `  hook  ...`, `  final ...`) so the output is easy to quote.
4. **Run live**: `uv run python lessons/lesson_NN_<topic>.py`. Fix failures. Record surprises as gotchas.
5. **Doc** `docs/lessons/lesson-NN-<topic>.md` using the 8-section template in `AGENTS.md`. Paste only real output.
6. **Update indexes**:
   - `README.md` lesson table.
   - `docs/sdk-concepts.md`: concept flowchart node + progress item.
   - `docs/sdk-coverage.md`: rows, statuses, score counts.
7. **Validate** with the `validate-docs` skill. Clean up temp files.
8. Report: what was built, observed output highlights, gotchas.
