---
name: sdk-upgrade-check
description: Compare the installed GitHub Copilot SDK (Python) version with the latest stable and preview releases, and map new or changed features to the lessons in this repo. Analysis only, no code changes. Use when a new SDK release appears or someone asks "what changed" or about a "new version".
---

# SDK upgrade check (analysis only)

Do **not** change code or dependencies. Report, then wait for the user to decide.

1. **Versions**
   ```bash
   uv pip show github-copilot-sdk | head -2
   curl -s https://pypi.org/pypi/github-copilot-sdk/json | python3 -c "import json,sys;print(json.load(sys.stdin)['info']['version'])"
   curl -s "https://api.github.com/repos/github/copilot-sdk/releases?per_page=15" \
     | python3 -c "import json,sys;[print(r['tag_name'],r['published_at'][:10],'preview' if r['prerelease'] else 'stable') for r in json.load(sys.stdin)]"
   ```
2. **What changed**: read `CHANGELOG.md` and the release bodies between the installed and the latest versions:
   `curl -s https://api.github.com/repos/github/copilot-sdk/releases/tags/<tag>`.
   Only trust these sources. Web summaries invent versions (for example a non-existent "SDK 2.0").
3. **Check the installed source** for each feature (see `verify-sdk-api`). Note that Python names differ from TypeScript names (`send_and_wait_typed` vs `sendAndWait`).
4. **Report** a table:

   | Feature | In installed? | Release | Lesson affected | Suggested change |
   |---|---|---|---|---|

   Use ✅ installed and unused, 🟡 preview only, ❌ not in Python yet, and ⚠️ breaking change.
5. Finish with a verdict (up to date or upgrade recommended) and the list of decisions for the user.
