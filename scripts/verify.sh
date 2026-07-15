#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

uv run ruff check backend
uv run pytest
npm --prefix frontend run test -- --run
npm --prefix frontend run build

[[ "$(codex login status 2>&1)" == *"Logged in using ChatGPT"* ]]
curl --fail --silent http://localhost:8080/health >/dev/null

echo "Static, test, OAuth, and DataHub checks passed."
