#!/usr/bin/env bash
# Render every Mermaid block in the given Markdown files (default: README.md + docs/**/*.md).
set -uo pipefail

ROOT=$(pwd)
FILES=("$@")
if [ ${#FILES[@]} -eq 0 ]; then
  mapfile -t FILES < <(ls README.md 2>/dev/null; find docs -name '*.md' | sort)
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

python3 - "$TMP" "${FILES[@]}" <<'EOF'
import re, sys, pathlib
tmp, files = sys.argv[1], sys.argv[2:]
n = 0
for f in files:
    for block in re.findall(r"```mermaid\n(.*?)```", pathlib.Path(f).read_text(), re.S):
        n += 1
        safe = f.replace("/", "__")
        pathlib.Path(tmp, f"{n:03d}__{safe}.mmd").write_text(block)
print(f"mermaid blocks: {n}")
EOF

cd "$TMP" || exit 1
ls ./*.mmd >/dev/null 2>&1 || exit 0
npm i -s @mermaid-js/mermaid-cli >/dev/null 2>&1
fail=0
for f in *.mmd; do
  if npx mmdc -q -i "$f" -o "${f%.mmd}.svg" >/dev/null 2>&1; then
    echo "ok   $f"
  else
    echo "FAIL $f"; fail=1
  fi
done
cd "$ROOT" || exit 1
exit $fail
