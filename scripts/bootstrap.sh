#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${CONTEXTLOOP_FAKE_CODEX:-0}" != "1" ]]; then
  if ! command -v codex >/dev/null 2>&1; then
    echo "Codex CLI is required. Install it, then run 'codex login'." >&2
    exit 1
  fi

  if [[ "$(codex login status 2>&1)" != *"Logged in using ChatGPT"* ]]; then
    echo "ChatGPT OAuth login is required. Run 'codex login'." >&2
    exit 1
  fi
else
  echo "Judge mode enabled: deterministic fixture, no model call."
fi

if ! command -v datahub >/dev/null 2>&1; then
  echo "DataHub CLI is required." >&2
  exit 1
fi

if ! curl --fail --silent http://localhost:8080/health >/dev/null 2>&1; then
  datahub docker quickstart --version v1.6.0 --dump-logs-on-failure
fi

datahub init --username datahub --password datahub --force >/dev/null 2>&1
datahub datapack load showcase-ecommerce
uv sync --locked
npm --prefix frontend ci

echo "ContextLoop prerequisites are ready. Run ./scripts/dev.sh"
