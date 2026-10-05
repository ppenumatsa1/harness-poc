---
name: validate-docs
description: Validate Markdown docs in this repo by checking relative links and rendering every Mermaid diagram. Use after creating or editing any file in docs/ or README.md.
---

# Validate docs

Run both scripts from the repo root:

```bash
python3 .github/skills/validate-docs/scripts/check_links.py
bash .github/skills/validate-docs/scripts/check_mermaid.sh            # all docs
bash .github/skills/validate-docs/scripts/check_mermaid.sh docs/lessons/lesson-13-skills-and-lifecycle-hooks.md   # one file
```

- `check_links.py`: every relative link in `README.md` and `docs/**/*.md` points to an existing file. Exit code 1 if any are broken.
- `check_mermaid.sh`: extracts each `mermaid` block and renders it with `@mermaid-js/mermaid-cli` in a temp folder. Prints `ok` or `FAIL` per block, then deletes the temp folder. Needs Node.js; the first run downloads the CLI.

Fix every failure before reporting the work as done. Common Mermaid fixes: quote labels with special characters (`A["x (y)"]`), use `<br/>` for line breaks, and avoid `;` inside labels.
