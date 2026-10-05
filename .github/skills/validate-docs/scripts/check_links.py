"""Check that every relative Markdown link in README.md and docs/ points to an existing file."""

import re
import sys
from pathlib import Path

LINK = re.compile(r"\]\(([^)#\s]+)")


def main() -> int:
    root = Path.cwd()
    files = [root / "README.md", root / "AGENTS.md", *root.glob("docs/**/*.md"), *root.glob(".github/**/*.md")]
    broken = 0
    for f in (f for f in files if f.exists()):
        for target in LINK.findall(f.read_text()):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (f.parent / target).exists():
                print(f"BROKEN {f.relative_to(root)} -> {target}")
                broken += 1
    print(f"checked {len(files)} files, broken links: {broken}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
