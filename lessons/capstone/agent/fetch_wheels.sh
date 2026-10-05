#!/usr/bin/env bash
# The Microsoft PyPI mirror has no github-copilot-sdk 1.0.16 (only rc builds), so the
# agent image installs it from ./wheels. Wheels are git-ignored: run this once before
# `docker compose build`. It downloads from public PyPI on the host.
set -euo pipefail
cd "$(dirname "$0")"
SDK_VERSION="${SDK_VERSION:-1.0.16}"
uv run --no-project --with pip python -m pip download "github-copilot-sdk==${SDK_VERSION}" \
  --no-deps --only-binary=:all: --dest wheels
ls -1 wheels
